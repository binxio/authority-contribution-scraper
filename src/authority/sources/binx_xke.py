import logging
import requests
import os, re
from datetime import datetime
from typing import Iterator

import feedparser
import pytz
from dateutil.parser import parse as datetime_parse

from authority.contribution import Contribution
from authority.sink import Sink
from authority.source import Source


class BinxXkeSource(Source):
    def __init__(self, sink: Sink):
        super(BinxXkeSource, self).__init__(sink)
        self.count = 0
        self.name = "https://xke.xebia.com/api/public"

    def feed(self) -> Iterator[Contribution]:
        self.count = 0
        latest = self.sink.latest_entry(unit="binx", contribution="xke")
        logging.info(
            "reading new XKE sessions from https://xke.xebia.com/api/public since %s",
            latest,
        )
        result = requests.get("https://xke.xebia.com/public/api/session/?unit=BINX")
        if result.status_code == 200:
            for session in result.json():
                date = datetime_parse(session["start_time"]).astimezone(
                    pytz.timezone("Europe/Amsterdam")
                )
                if date > latest:
                    presenters = map(
                        lambda p: p.strip(),
                        re.findall(r"[\w\s]+", session["presenter"]),
                    )
                    for presenter in presenters:
                        url = (
                            f"https://xke.xebia.com/event/{date.date()}/{session['id']}"
                        )
                        contribution = Contribution(
                            guid=url,
                            title=session["title"],
                            author=presenter,
                            date=date,
                            url=url,
                            unit="binx",
                            type="xke",
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
    src = BinxXkeSource(sink)
    for c in src.feed():
        print(c)
