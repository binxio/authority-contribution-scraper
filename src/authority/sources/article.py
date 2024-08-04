"""
Module containing the articles source class
"""
import logging
import typing
from datetime import datetime
from time import mktime

import feedparser
import pytz
import requests
from dateutil.parser import parse as datetime_parse

from authority.model.contribution import Contribution
from authority.sources.base_ import AuthoritySource

if typing.TYPE_CHECKING:
    import collections.abc


class ArticleSource(AuthoritySource):
    """
    Articles scraper implementation
    """

    @property
    def name(self) -> str:
        return "articles.xebia.com"

    @classmethod
    def scraper_id(cls) -> str:
        return "articles.xebia.com"

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
        now = datetime.now(tz=pytz.utc)
        logging.info(
            "reading new blogs from https://articles.xebia.com/rss.xml since %s", latest
        )
        feed = feedparser.parse("https://articles.xebia.com/rss.xml", modified=latest)

        for entry in sorted(feed.entries, key=lambda e: e["published_parsed"]):
            published_date = datetime.fromtimestamp(
                mktime(entry["published_parsed"]), tz=pytz.utc
            )
            if published_date > latest or published_date.date() == now.date():
                yield from self._process_article(entry, published_date)

    def _process_article(
        self,
        entry: dict,
        published_date: datetime,
    ) -> "collections.abc.Generator[Contribution, None, None]":
        for author in entry["authors"]:
            if not author.get("name"):
                logging.error('article without author "%s"', entry["id"])
                continue

            contribution = Contribution(
                guid=entry["id"],
                author=author["name"],
                date=published_date,
                title=entry["title"],
                url=entry["link"],
                scraper_id=self.scraper_id(),
                type=self._contribution_type,
            )
            yield contribution


if __name__ == "__main__":
    from authority.util.test_source import test_source

    test_source(source=ArticleSource)
