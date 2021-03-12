import logging
import requests
import os, re
from datetime import datetime
from typing import Iterator

import pytz
from dateutil.parser import parse as datetime_parse

from authority.contribution import Contribution
from authority.sink import Sink
from authority.source import Source
from typing import List


def split_presenters(p:str) -> List[str]:
    p = re.sub(r"\.", "", p)        # remove dots from names
    p = re.sub(r"\([^)]*\)", "", p)  # remove stuff between brackets
    p = re.sub(r" vd ", " van de ", p)  # especially for Martijn :-)
    result = list(filter(lambda s : s, map(lambda s : s.strip(), re.split(r"- | -|,|\&+|/| en | and ", p))))
    return result if result else [p]


class BinxXkeSource(Source):
    def __init__(self, sink: Sink):
        super(BinxXkeSource, self).__init__(sink)
        self.count = 0
        self.name = "https://xke.xebia.com/api/public"

    def feed(self) -> Iterator[Contribution]:
        self.count = 0
        latest = self.sink.latest_entry(unit="binx", contribution="xke")
        logging.info(
            "reading new XKE sessions from https://xke-nxt.appspot.com/api/ since %s",
            latest,
        )
        now = datetime.now().astimezone(pytz.utc)
        result = requests.get("https://xke-nxt.appspot.com/api/session/?unit=BINX")
        if result.status_code == 200:
            for session in result.json():
                xke_date = session["xke"].rstrip("/").split("/")[-1]
                start_time = f"{xke_date}T{session['start_time']}"
                date = datetime_parse(start_time).astimezone(
                    pytz.timezone("Europe/Amsterdam")
                )

                if date > latest and date < now:
                    for presenter in split_presenters(session["presenter"]):
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
