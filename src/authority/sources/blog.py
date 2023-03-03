"""
Module containing the Blog source class
"""
import logging
import typing
from datetime import datetime

import pytz
import requests
from dateutil.parser import parse as datetime_parse

from authority.model.contribution import Contribution
from authority.sources.base_ import AuthoritySource
from authority.util.unit import get_unit_from_user

if typing.TYPE_CHECKING:
    import collections.abc


class BlogSource(AuthoritySource):
    """
    Blog scraper implementation
    """

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

    @property
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":
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
    ) -> "collections.abc.Generator[Contribution, None, None]":
        for author in entry["_embedded"]["author"]:
            author_name = author.get("name")
            if not author_name:
                continue
            ms_user = self._ms_graph_api.get_user_by_display_name(
                display_name=author_name
            )
            if not ms_user:
                continue
            unit = get_unit_from_user(user=ms_user)
            if not unit:
                continue
            contribution = Contribution(
                guid=entry["guid"]["rendered"],
                author=author["name"],
                date=published_date,
                title=entry["title"]["rendered"],
                url=entry["link"],
                unit=unit,
                scraper_id=self.scraper_id(),
                type=self._contribution_type,
            )
            yield contribution


if __name__ == "__main__":
    from authority.util.test_source import test_source

    test_source(source=BlogSource)
