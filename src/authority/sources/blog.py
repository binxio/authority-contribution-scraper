"""
Module containing the Blog source class
"""

import configparser
import logging
from datetime import datetime, timedelta
from os.path import expanduser

import pytz
import requests
from dateutil.parser import parse as datetime_parse

from authority.model.contribution import Contribution
from authority.sources.base_ import AuthoritySource
from typing import Generator
from functools import cache

from authority.util.google_secrets import SecretManager
from authority.util.lazy_env import lazy_env


class BlogSource(AuthoritySource):
    """
    Blog scraper implementation
    """

    def __init__(self, sink):
        super().__init__(sink)
        config = configparser.ConfigParser()
        config.read(expanduser("~/.wordpress.ini"))
        self.username = lazy_env(
            key="WP_USERNAME",
            default=lambda: SecretManager().get_secret(
                "authority-contribution-wordpress-username"
            ),
        )
        self.password = lazy_env(
            key="WP_PASSWORD",
            default=lambda: SecretManager().get_secret(
                "authority-contribution-wordpress-password"
            ),
        )

    @property
    def name(self) -> str:
        return "xebia.com"

    @classmethod
    def scraper_id(cls) -> str:
        return "xebia.com/blog"

    @property
    def _contribution_type(self) -> str:
        return "blog"

    def _get_latest_entry(self) -> datetime:
        return self.sink.latest_entry(
            type=self._contribution_type, scraper_id=self.scraper_id()
        )

    @cache
    def _get_author_by_id(self, author_id:str) -> [str]:
        response = requests.get(
            url=f"https://xebia.com/wp-json/wp/v2/users/",
            auth=(self.username, self.password),
            params={"search": author_id},
            headers={"User-Agent": "curl", "Accept": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            authors = list(map(lambda x: x["name"], filter(lambda x: x["id"] == author_id, response.json())))
            return [response.json().get("name")]
        else:
            logging.error( f"could nog get author by id {author_id} from {response.url}. {response.text}")
            return []

    @property
    def _feed(self) -> Generator[Contribution, None, None]:
        latest = self._get_latest_entry()
        logging.info(
            "reading new blogs from https://xebia.com.com/blog since %s", latest
        )
        now = datetime.now().astimezone(pytz.utc)

        page = 1
        total_pages = 1

        after = latest.astimezone(pytz.UTC).replace(tzinfo=None).isoformat()
        while page <= total_pages:
            response = requests.get(
                url="https://xebia.com/wp-json/wp/v2/posts",
                auth=(self.username, self.password),
                params={
                    "page": page,
                    "per_page": 50,
                    "order": "asc",
                    "orderby": "date",
                    "after": after,
                    "_embed": "author",
                },
                headers={"User-Agent": "curl", "Accept": "application/json"},
                timeout=10,
            )
            if response.status_code != 200:
                raise ValueError(
                    f"could nog get posts from {response.url}. {response.text}"
                )

            page = page + 1
            total_pages = int(response.headers["X-WP-TotalPages"])

            for entry in response.json():
                published_date = datetime_parse(entry["date_gmt"]).astimezone(pytz.utc)
                if latest < published_date < now:
                    yield from self._process_blogpost_entry(entry, published_date)

    def _process_blogpost_entry(
        self,
        entry: dict,
        published_date: datetime,
    ) -> Generator[Contribution, None, None]:
        authors = list(
            map(
                lambda a: a["name"],
                filter(lambda a: "name" in a, entry.get("_embedded", {}).get("author")),
            )
        )
        if not authors:
            authors = self._get_author_by_id(entry.get("author"))

        if not authors:
            logging.error('blog without author "%s"', entry["link"])
            return

        for author in authors:
            contribution = Contribution(
                guid=entry["guid"]["rendered"],
                author=author,
                date=published_date,
                title=entry["title"]["rendered"],
                url=entry["link"],
                scraper_id=self.scraper_id(),
                type=self._contribution_type,
            )
            yield contribution


if __name__ == "__main__":
    from authority.util.test_source import test_source

    test_source(
        source=BlogSource,
        latest_entry=(
            datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            - timedelta(days=30)
        ).astimezone(pytz.utc),
    )
