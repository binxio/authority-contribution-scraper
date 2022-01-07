import logging
import requests
import os, re
from datetime import datetime
from typing import Iterator

import pytz

from authority.contribution import Contribution
from authority.sink import Sink
from authority.source import Source
from typing import List
from google.cloud import firestore


def split_presenters(p: str) -> List[str]:
    p = re.sub(r"\.", "", p)  # remove dots from names
    p = re.sub(r"\([^)]*\)", "", p)  # remove stuff between brackets
    p = re.sub(r" vd ", " van de ", p)  # especially for Martijn :-)
    result = list(
        filter(
            lambda s: s,
            map(lambda s: s.strip(), re.split(r"- | -|,|\&+|/| en | and ", p)),
        )
    )
    return result if result else [p]


class BinxXkeSource(Source):
    def __init__(self, sink: Sink):
        super(BinxXkeSource, self).__init__(sink)
        self.count = 0
        self.db = firestore.Client(project="xke-nxt")

    def feed(self) -> Iterator[Contribution]:
        self.count = 0
        latest = self.sink.latest_entry(unit="binx", contribution="xke")
        logging.info(
            "reading new XKE sessions from firestore since %s",
            latest,
        )
        now = datetime.now().astimezone(pytz.utc)
        events = self.db.collection("events").where("startTime", ">=", latest)

        for event in events.stream():
            for session_type in ["sessions-public", "sessions-private"]:
                for session in (
                    self.db.collection("events")
                    .document(event.id)
                    .collection(session_type)
                    .where("unit.id", "==", "BINX")
                    .stream()
                ):
                    s = session.to_dict()
                    start_time = s.get("startTime", None)
                    if not start_time:
                        logging.error(
                            "%s - %s - does not have a startTime field",
                            event.id,
                            session.id,
                        )
                        continue

                    presenters = s.get("presenter", None)
                    if not presenters:
                        logging.error(
                            "%s - %s - does not have a presenter field",
                            event.id,
                            session.id,
                        )
                        continue
                    title = s.get("title", None)
                    if not title:
                        logging.error(
                            "%s - %s - does not have a title field",
                            event.id,
                            session.id,
                        )
                        continue

                    url = f"https://xke.xebia.com/event/{event.id}/{session.id}/{s.get('slug','')}"

                    if latest < start_time < now:
                        for presenter in split_presenters(presenters):
                            contribution = Contribution(
                                guid=url,
                                title=title,
                                author=presenter,
                                date=start_time,
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
