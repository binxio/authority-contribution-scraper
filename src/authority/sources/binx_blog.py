import logging
import os
from datetime import datetime
from typing import Iterator

import feedparser
import pytz
from dateutil.parser import parse as datetime_parse

from authority.contribution import Contribution
from authority.sink import Sink
from authority.source import Source


class BinxBlogSource(Source):
    def __init__(self, sink: Sink):
        super(BinxBlogSource, self).__init__(sink)
        self.count = 0
        self.name = "https://binx.io/blog"

    def feed(self) -> Iterator[Contribution]:
        self.count = 0
        latest = self.sink.latest_entry(unit="binx", contribution="blog")
        logging.info("reading new blogs from https://binx.io/blog since %s", latest)
        now = datetime.now().astimezone(pytz.utc)
        feed = feedparser.parse("https://binx.io/blog/index.xml")
        for entry in feed.entries:
            published_date = datetime_parse(entry["published"]).astimezone(pytz.utc)
            if published_date > latest and published_date < now:
                for author in entry["authors"]:
                    contribution = Contribution(
                        guid=entry["guid"],
                        author=author["name"],
                        date=published_date,
                        title=entry["title"],
                        url=entry["link"],
                        unit="binx",
                        type="blog",
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
    src = BinxBlogSource(sink)
    for c in src.feed():
        print(c)
