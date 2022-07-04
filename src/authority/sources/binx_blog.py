import logging
import os
from datetime import datetime
from typing import Iterator

import feedparser
import pytz
import requests
from dateutil.parser import parse as datetime_parse

from authority.contribution import Contribution
from authority.sink import Sink
from authority.source import Source


class BinxBlogSource(Source):
    def __init__(self, sink: Sink):
        super(BinxBlogSource, self).__init__(sink)
        self.count = 0
        self.users: dict[int, str] = {}

    def get_user(self, user_id: int):
        if user_id not in self.users:
            response = requests.get(
                f"https://binx.wpengine.com/wp-json/wp/v2/users/{user_id}",
                headers={"User-Agent": "curl", "Accept": "application/json"},
            )
            assert response.status_code == 200
            self.users[user_id] = response.json()["name"]

        return self.users[user_id]

    def feed(self) -> Iterator[Contribution]:
        self.count = 0
        latest = self.sink.latest_entry(unit="binx", contribution="blog")
        logging.info(
            "reading new blogs from https://binx.wpengine.com/blog since %s", latest
        )
        now = datetime.now().astimezone(pytz.utc)

        page = 1
        total_pages = 1

        after = latest.astimezone(pytz.UTC).replace(tzinfo=None).isoformat()
        while page <= total_pages:
            response = requests.get(
                "https://binx.wpengine.com/wp-json/wp/v2/posts",
                params={
                    "page": page,
                    "per_page": 50,
                    "order": "asc",
                    "orderby": "date",
                    "after": after,
                },
                headers={"User-Agent": "curl", "Accept": "application/json"},
            )
            if response.status_code != 200:
                raise ValueError(
                    f"could nog get posts from {response.url}. {response.text}"
                )

            page = page + 1
            total_pages = int(response.headers["X-WP-TotalPages"])

            for entry in response.json():
                published_date = datetime_parse(entry["date_gmt"]).astimezone(pytz.utc)
                if published_date > latest and published_date < now:
                    contribution = Contribution(
                        guid=entry["guid"]["rendered"],
                        author=self.get_user(entry["author"]),
                        date=published_date,
                        title=entry["title"]["rendered"],
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
