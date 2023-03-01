import functools
import logging
import typing
from copy import deepcopy
from datetime import datetime, date
from time import time, sleep
from urllib.parse import urlparse

import requests.utils

from authority.contribution import Contribution
from authority.google_secrets import SecretManager
from authority.sources.base_ import Source
from authority.util.lazy_env import lazy_env

if typing.TYPE_CHECKING:
    import collections.abc
    from requests.structures import CaseInsensitiveDict
    from authority.sink import Sink


class GithubPullRequests(Source):
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
    def contribution_type(self) -> str:
        return "github-pr"

    @classmethod
    def scraper_id(cls) -> str:
        return "github.com/binxio"

    def add_authorization(self, kwargs):
        if self.token:
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Token {self.token}"
            kwargs["headers"] = headers

    def get_rate_limited(self, url, **kwargs) -> tuple[typing.Any, "CaseInsensitiveDict[str]"]:
        self.add_authorization(kwargs)
        while True:
            response = self.session.get(url, **kwargs)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as exception:
                if response.status_code != 403:
                    raise exception
                rate_limit = response.headers.get("X-RateLimit-Remaining")
                if rate_limit != "0":
                    continue
                reset_time = response.headers.get("X-RateLimit-Reset")
                wait_time = int(int(reset_time) - time()) + 1
                if wait_time == 0:
                    continue
                logging.info("rate limited, sleeping %s seconds", wait_time)
                sleep(wait_time)
                continue

            return response.json(), response.headers

    @staticmethod
    def get_next_link(headers) -> typing.Optional[str]:
        links = requests.utils.parse_header_links(headers.get("link", ""))
        return next(
            map(lambda link: link["url"], filter(lambda link: link.get("rel") == "next", links)),
            None,
        )

    def get_paginated(self, url, **kwargs) -> "collections.abc.Generator[typing.Any, None, None]":
        response, headers = self.get_rate_limited(url, **kwargs)
        yield response

        next_url = self.get_next_link(headers)
        while next_url:
            response, headers = self.get_rate_limited(next_url)
            yield response
            next_url = self.get_next_link(headers)

    @functools.lru_cache(maxsize=0, typed=True)
    def get_user_info(self, username: str) -> dict:
        response, _ = self.get_rate_limited(f"https://api.github.com/users/{username}")
        if not response.get("name"):
            logging.info("no display name for %s", username)
            response["name"] = username

        return deepcopy(response)

    @property
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        latest = self.sink.latest_entry(unit="binx", type=self.contribution_type).date()
        if latest < date(year=2018, month=1, day=1):
            latest = date(year=2018, month=1, day=1)

        for org_members in self.get_paginated(
            "https://api.github.com/orgs/binxio/members"
        ):
            yield from self._process_org_members(latest, org_members)

    def _process_org_members(self, latest: date, org_members: list[dict]):
        for member in org_members:
            query = " ".join(
                (
                    "is:pr",
                    "is:merged",
                    f"closed:>{latest.isoformat()}",
                    f"author:{member['login']}",
                )
            )

            for prs in self.get_paginated(
                    "https://api.github.com/search/issues", params={"q": query}
            ):
                user = self.get_user_info(member["login"])

                for pr in prs["items"]:
                    url = urlparse(pr["url"])
                    if url.path.startswith(f"/repos/{member['login']}"):
                        # PRs on your own repo? unfortunately they are not counted
                        continue

                    closed_at = datetime.strptime(
                        pr["closed_at"], "%Y-%m-%dT%H:%M:%SZ"
                    )
                    if closed_at.date() == date.today():
                        # skip PRs that are closed today, to ensure we get all PRs.
                        continue

                    repository = "/".join(url.path.split("/")[2:4])
                    contribution = Contribution(
                        guid=pr["url"],
                        author=user["name"],
                        date=datetime.strptime(
                            pr["closed_at"], "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        title=f'{repository} - {pr["title"]}',
                        unit="cloud",
                        type=self.contribution_type,
                        scraper_id=self.scraper_id(),
                        url=pr["url"],
                    )
                    yield contribution


if __name__ == "__main__":
    from pathlib import Path
    import csv
    import dataclasses
    import os
    from authority.sink import Sink
    import pytz

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    sink = Sink()
    sink.latest_entry = lambda **kwargs: datetime.fromordinal(1).replace(
        tzinfo=pytz.utc
    )
    src = GithubPullRequests(sink)
    with Path("./pr_output.csv").open(mode="w") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(field.name for field in dataclasses.fields(Contribution)))
        writer.writeheader()
        for c in src.feed:
            writer.writerow(dataclasses.asdict(c))
    print(f"{src.count} merged pull requests found.")
