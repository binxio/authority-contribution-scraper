"""
Module containing the GitHub Pull Request source class
"""
import functools
import logging
import typing
from copy import deepcopy
from datetime import datetime, date, timezone
from time import time, sleep

import requests.utils

from authority.model.contribution import Contribution
from authority.sources.base_ import AuthoritySource
from authority.util.google_secrets import SecretManager
from authority.util.lazy_env import lazy_env
from typing import Dict

if typing.TYPE_CHECKING:
    import collections.abc
    from requests.structures import CaseInsensitiveDict
    from authority.sink import Sink

_GRAPHQL_URL = "https://api.github.com/graphql"
_GRAPHQL_BATCH_SIZE = 20
_MIN_HISTORY_DATE = date(year=2018, month=1, day=1)

_SEARCH_PRS_QUERY = """
query($query: String!, $cursor: String) {
  search(query: $query, type: ISSUE, first: 100, after: $cursor) {
    issueCount
    nodes {
      ... on PullRequest {
        number
        title
        closedAt
        author {
          login
          ... on User { name }
        }
        repository { nameWithOwner }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
  rateLimit { remaining cost resetAt }
}
"""


class GithubPullRequests(AuthoritySource):
    """
    GitHub PR scraper implementation
    """

    def __init__(self, sink: "Sink"):
        super().__init__(sink)
        self.session = requests.Session()
        self.token = lazy_env(
            key="GITHUB_API_TOKEN",
            default=lambda: SecretManager().get_secret(
                "authority-contribution-scraper-github-api-token"
            ),
        )

    @property
    def name(self) -> str:
        return "github-pull-requests"

    @property
    def _contribution_type(self) -> str:
        return "github-pr"

    @classmethod
    def scraper_id(cls) -> str:
        return "github.com/binxio"

    def _add_authorization(self, kwargs):
        if self.token:
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Token {self.token}"
            kwargs["headers"] = headers

    def _get_rate_limited(
        self, url, **kwargs
    ) -> tuple[typing.Any, "CaseInsensitiveDict[str]"]:
        self._add_authorization(kwargs)
        while True:
            try:
                response = self.session.get(url, **kwargs)
                response.raise_for_status()
            except requests.exceptions.ConnectionError as error:
                wait_time = 10
                logging.warning("failed to connect to GitHub API: %s", error)
                logging.info("retry in %s seconds", wait_time)
                sleep(wait_time)
                continue
            except requests.exceptions.HTTPError as exception:
                if response.status_code != 403:
                    raise exception
                rate_limit = response.headers.get("X-RateLimit-Remaining")
                if rate_limit != "0":
                    continue
                self.session = requests.Session()
                reset_time = response.headers.get("X-RateLimit-Reset")
                wait_time = int(int(reset_time) - time()) + 1 if reset_time else 0
                if wait_time == 0:
                    continue
                logging.info("rate limited, sleeping %s seconds", wait_time)
                sleep(wait_time)
                continue

            return response.json(), response.headers

    @staticmethod
    def _get_next_link(headers) -> typing.Optional[str]:
        links = requests.utils.parse_header_links(headers.get("link", ""))
        return next(
            map(
                lambda link: link["url"],
                filter(lambda link: link.get("rel") == "next", links),
            ),
            None,
        )

    def _get_paginated(
        self, url, **kwargs
    ) -> "collections.abc.Generator[typing.Any, None, None]":
        response, headers = self._get_rate_limited(url, **kwargs)
        yield response

        next_url = self._get_next_link(headers)
        while next_url:
            response, headers = self._get_rate_limited(next_url)
            yield response
            next_url = self._get_next_link(headers)

    @functools.lru_cache(maxsize=64, typed=True)
    def _get_user_info(self, username: str) -> dict:
        response, _ = self._get_rate_limited(f"https://api.github.com/users/{username}")
        if not response.get("name"):
            logging.info("no display name for %s", username)
            response["name"] = username

        return deepcopy(response)

    def _graphql_post(self, query: str, variables: dict) -> dict:
        """Make a GraphQL POST request to the GitHub API with rate limit handling."""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        while True:
            try:
                response = self.session.post(
                    _GRAPHQL_URL,
                    json={"query": query, "variables": variables},
                    headers=headers,
                )
                response.raise_for_status()
            except requests.exceptions.ConnectionError as error:
                logging.warning("failed to connect to GitHub GraphQL API: %s", error)
                sleep(10)
                continue
            except requests.exceptions.HTTPError as exception:
                if response.status_code == 403:
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    wait_time = int(int(reset_time) - time()) + 1 if reset_time else 60
                    logging.info("GraphQL rate limited, sleeping %s seconds", wait_time)
                    sleep(wait_time)
                    continue
                raise

            data = response.json()

            # GraphQL errors arrive as HTTP 200 with an "errors" key
            if "errors" in data:
                fatal_errors = []
                for error in data["errors"]:
                    if error.get("type") == "RATE_LIMITED":
                        reset_time = response.headers.get("X-RateLimit-Reset")
                        wait_time = int(int(reset_time) - time()) + 1 if reset_time else 60
                        logging.info(
                            "GraphQL rate limited (response body), sleeping %s seconds",
                            wait_time,
                        )
                        sleep(wait_time)
                        break
                    elif error.get("type") == "FORBIDDEN":
                        logging.warning(
                            "GraphQL FORBIDDEN for node at path %s: %s",
                            error.get("path"),
                            error.get("message"),
                        )
                    else:
                        fatal_errors.append(error)
                else:
                    if fatal_errors:
                        raise RuntimeError(f"GraphQL errors: {fatal_errors}")
                    # Only FORBIDDEN/warnings — continue with partial data
                    return data["data"]
                continue

            # Log and proactively back off when the point budget runs low
            rate_limit = (data.get("data") or {}).get("rateLimit")
            if rate_limit:
                logging.debug(
                    "GraphQL rate limit: %d remaining (cost %d)",
                    rate_limit["remaining"],
                    rate_limit["cost"],
                )
                if rate_limit["remaining"] < 100:
                    reset_at = datetime.fromisoformat(
                        rate_limit["resetAt"].replace("Z", "+00:00")
                    )
                    wait_time = max(
                        0,
                        int((reset_at - datetime.now(timezone.utc)).total_seconds()) + 1,
                    )
                    logging.info(
                        "GraphQL rate limit low (%d remaining), sleeping %s seconds",
                        rate_limit["remaining"],
                        wait_time,
                    )
                    sleep(wait_time)

            return data["data"]

    def _graphql_search_page(
        self, query_str: str, cursor: typing.Optional[str] = None
    ) -> tuple[int, list, bool, typing.Optional[str]]:
        """Fetch one page of GraphQL search results.

        Returns (issueCount, nodes, hasNextPage, endCursor).
        """
        data = self._graphql_post(_SEARCH_PRS_QUERY, {"query": query_str, "cursor": cursor})
        search = data["search"]
        return (
            search["issueCount"],
            search["nodes"],
            search["pageInfo"]["hasNextPage"],
            search["pageInfo"].get("endCursor"),
        )

    def _contribution_from_pr_node(
        self,
        node: dict,
        login_to_member: Dict[str, dict],
        latest_by_login: Dict[str, date],
    ) -> typing.Optional[Contribution]:
        """Convert a GraphQL PR node to a Contribution, or None if it should be skipped."""
        if not node:
            return None
        author = node.get("author")
        if not author:
            return None
        login = author.get("login")
        if not login or login not in login_to_member:
            return None

        closed_at = datetime.strptime(node["closedAt"], "%Y-%m-%dT%H:%M:%SZ")
        if closed_at.date() == date.today():
            return None

        user_latest = latest_by_login.get(login, _MIN_HISTORY_DATE)
        if closed_at.date() <= user_latest:
            return None

        member = login_to_member[login]
        repo_name = node["repository"]["nameWithOwner"]
        # Preserve the same GUID/URL format as the REST search endpoint
        api_url = f"https://api.github.com/repos/{repo_name}/issues/{node['number']}"
        return Contribution(
            guid=api_url,
            author=member["name"],
            date=closed_at,
            title=f'{repo_name} - {node["title"]}',
            type=self._contribution_type,
            scraper_id=self.scraper_id(),
            url=api_url,
        )

    def _process_member_batch(
        self,
        batch: list[dict],
        latest_by_login: Dict[str, date],
    ) -> "collections.abc.Generator[Contribution, None, None]":
        """Search PRs for a batch of members via a single GraphQL query.

        Recursively splits the batch in half when GitHub's 1 000-result cap is
        reached so that no contributions are silently dropped.
        """
        if not batch:
            return

        batch_min_date = min(
            latest_by_login.get(m["login"], _MIN_HISTORY_DATE) for m in batch
        )
        login_to_member = {m["login"]: m for m in batch}
        author_filters = " ".join(f"author:{m['login']}" for m in batch)
        search_q = f"is:pr is:merged closed:>{batch_min_date.isoformat()} {author_filters}"

        try:
            issue_count, nodes, has_next, cursor = self._graphql_search_page(search_q)
        except RuntimeError as e:
            if len(batch) > 1:
                logging.warning("GraphQL batch query failed, splitting batch: %s", e)
                mid = len(batch) // 2
                yield from self._process_member_batch(batch[:mid], latest_by_login)
                yield from self._process_member_batch(batch[mid:], latest_by_login)
                return
            logging.warning(
                "GraphQL query failed for user %s, skipping: %s", batch[0]["login"], e
            )
            return

        if issue_count > 1000 and len(batch) > 1:
            logging.info(
                "Batch of %d users has %d results (>1000), splitting into sub-batches",
                len(batch),
                issue_count,
            )
            mid = len(batch) // 2
            yield from self._process_member_batch(batch[:mid], latest_by_login)
            yield from self._process_member_batch(batch[mid:], latest_by_login)
            return

        if issue_count > 1000:
            logging.warning(
                "User %s has over 1000 results, some PRs may be missed",
                batch[0]["login"],
            )

        while True:
            for node in nodes:
                contribution = self._contribution_from_pr_node(
                    node, login_to_member, latest_by_login
                )
                if contribution:
                    yield contribution
            if not has_next:
                break
            _, nodes, has_next, cursor = self._graphql_search_page(search_q, cursor)

    @property
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        # Collect all unique members across orgs, resolving display names
        processed = set()
        processed.add("admin-xebia")
        all_members: list[dict] = []
        for organization in ["binxio", "OblivionCloudControl", "xebia"]:
            for org_members in self._get_paginated(
                f"https://api.github.com/orgs/{organization}/members"
            ):
                for member in org_members:
                    login = member["login"]
                    if login in processed:
                        continue
                    processed.add(login)
                    user = self._get_user_info(login)
                    all_members.append({"login": login, "name": user["name"]})

        # Single BigQuery query replaces one query per member
        all_latest = self.sink.latest_entries_by_author(
            type=self._contribution_type,
            scraper_id=self.scraper_id(),
        )
        latest_by_login: Dict[str, date] = {}
        for m in all_members:
            latest_dt = all_latest.get(m["name"])
            latest_date = latest_dt.date() if latest_dt else _MIN_HISTORY_DATE
            if latest_date < _MIN_HISTORY_DATE:
                latest_date = _MIN_HISTORY_DATE
            latest_by_login[m["login"]] = latest_date

        # Batched GraphQL search replaces one REST search call per member
        for i in range(0, len(all_members), _GRAPHQL_BATCH_SIZE):
            batch = all_members[i : i + _GRAPHQL_BATCH_SIZE]
            yield from self._process_member_batch(batch, latest_by_login)


if __name__ == "__main__":
    import csv
    import dataclasses
    import logging
    import os
    from pathlib import Path
    from time import perf_counter
    from unittest.mock import MagicMock

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    _start = perf_counter()

    if not os.getenv("GITHUB_API_TOKEN"):
        logging.warning("GITHUB_API_TOKEN not set — running unauthenticated (60 req/hr limit)")

    mock_sink = MagicMock()
    mock_sink.latest_entries_by_author.return_value = {}

    src = GithubPullRequests(sink=mock_sink)
    output_path = Path("./github_output.csv")
    with output_path.open(mode="w", encoding="UTF-8", newline="") as file:
        from authority.model.contribution import Contribution

        fieldnames = tuple(field.name for field in dataclasses.fields(Contribution))
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for contribution in src.feed:
            writer.writerow(dataclasses.asdict(contribution))
            print(contribution)

    print(f"\n{src.count} merged pull requests found. Written to {output_path}")
    elapsed = perf_counter() - _start
    print(f"Run completed in {elapsed:.1f}s ({elapsed/60:.1f} min)")
