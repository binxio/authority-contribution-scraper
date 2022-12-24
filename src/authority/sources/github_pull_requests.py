import logging
import os
from datetime import datetime, date
from time import time, sleep
from typing import Iterator, Optional
from urllib.parse import urlparse
from copy import deepcopy

import pytz
import requests
import functools

from authority.contribution import Contribution
from authority.sink import Sink
from authority.source import Source
from authority.google_secrets import SecretManager


class GithubPullRequests(Source):
    def __init__(self, sink: Sink):
        super(GithubPullRequests, self).__init__(sink)
        self.count = 0
        self.name = "github-pull-requests"
        self.session = requests.Session()
        self.token = os.getenv(
            "GITHUB_API_TOKEN",
            SecretManager.get_instance().get_secret(
                "authority-contribution-scraper-github-api-token"
            ),
        )

    def add_authorization(self, kwargs):
        if self.token:
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Token {self.token}"
            kwargs["headers"] = headers

    def get_rate_limited(self, url, **kwargs) -> (dict, dict):
        self.add_authorization(kwargs)
        while True:
            response = self.session.get(url, **kwargs)
            if response.status_code == 200:
                return response.json(), response.headers

            if response.status_code == 403:
                rate_limit = response.headers.get("X-RateLimit-Remaining")
                if rate_limit == "0":
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    wait_time = int(int(reset_time) - time()) + 1
                    if wait_time > 0:
                        logging.info("rate limited, sleeping %s seconds", wait_time)
                        sleep(wait_time)
            else:
                raise Exception(
                    f"server return status {response.status_code}, {response.text}"
                )

    @staticmethod
    def get_next_link(headers) -> Optional[str]:
        links = requests.utils.parse_header_links(headers.get("link", ""))
        return next(
            map(lambda l: l["url"], filter(lambda l: l.get("rel") == "next", links)),
            None,
        )

    def get_paginated(self, url, **kwargs) -> dict:
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
            logging.info("no user name for %s", username)
            response["name"] = username

        return deepcopy(response)

    def feed(self) -> Iterator[Contribution]:
        self.count = 0
        latest = self.sink.latest_entry(unit="binx", contribution="github-pr").date()
        if latest < date(year=2018, month=1, day=1):
            latest = date(year=2018, month=1, day=1)

        for org_members in self.get_paginated(
            "https://api.github.com/orgs/binxio/members"
        ):
            for member in org_members:
                query = " ".join(
                    [
                        "is:closed",
                        "is:pr",
                        "is:merged",
                        f"closed:>{latest.isoformat()}",
                        f"author:{member['login']}",
                    ]
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
                            unit="binx",
                            type="github-pr",
                            url=pr["url"],
                        )
                        self.count = self.count + 1
                        yield contribution


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    sink = Sink()
    sink.latest_entry = lambda unit, contribution: datetime.fromordinal(1).replace(
        tzinfo=pytz.utc
    )
    src = GithubPullRequests(sink)
    for c in src.feed():
        print(c)
