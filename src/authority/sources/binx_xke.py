import logging
import os
import re
from datetime import datetime
from typing import Iterator, List

import pytz
import google
import gcloud_config_helper
from google.cloud import firestore
from authority.contribution import Contribution
from authority.sink import Sink
from authority.source import Source


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


def create_from_document(
    event, session: firestore.DocumentSnapshot
) -> Iterator[Contribution]:
    s = session.to_dict()
    start_time = s.get("startTime", None)
    if not start_time:
        logging.error(
            "%s - %s - does not have a startTime field",
            event.id,
            session.id,
        )
        return None

    presenters = s.get("presenter", None)
    if not presenters:
        logging.error(
            "%s - %s - does not have a presenter field",
            event.id,
            session.id,
        )
        return None

    title = s.get("title", None)
    if not title:
        logging.error(
            "%s - %s - does not have a title field",
            event.id,
            session.id,
        )
        return None

    url = f"https://xke.xebia.com/event/{event.id}/{session.id}/{s.get('slug','')}"

    for presenter in split_presenters(presenters):
        yield Contribution(
            guid=url,
            title=title,
            author=presenter,
            date=start_time,
            url=url,
            unit="binx",
            type="xke",
        )


class BinxXkeSource(Source):
    def __init__(self, sink: Sink):
        super(BinxXkeSource, self).__init__(sink)
        self.count = 0
        self.name = "firestore"
        if gcloud_config_helper.on_path():
            credentials, _ = gcloud_config_helper.default()
        else:
            logging.info("using application default credentials")
            credentials, _ = google.auth.default()
        self.db = firestore.Client(credentials=credentials, project="xke-nxt")

    def feed(self) -> Iterator[Contribution]:
        self.count = 0
        latest = self.sink.latest_entry(unit="binx", contribution="xke")

        logging.info(
            "reading new XKE sessions from firestore since %s",
            latest,
        )

        now = datetime.now().astimezone(pytz.utc)
        events = (
            self.db.collection("events")
            .where(
                "startTime",
                ">=",
                latest.replace(hour=0, minute=0, second=0, microsecond=0),
            )
            .order_by("startTime")
        )

        for event in events.stream():
            contributions: List[Contribution] = []
            for session in (
                self.db.collection("events")
                .document(event.id)
                .collection("sessions-public")
                .where("unit.id", "==", "BINX")
                .stream()
            ):
                for contribution in create_from_document(event, session):
                    contributions.append(contribution)

            contributions.sort(key=lambda x: x.date)

            for contribution in contributions:
                if latest < contribution.date < now:
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
