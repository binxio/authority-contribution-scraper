import abc
import logging
import os
import re
import typing
from datetime import datetime

import gcloud_config_helper
import google
import pytz
from google.cloud import firestore

from authority.contribution import Contribution
from authority.sink import Sink
from authority.source import Source

if typing.TYPE_CHECKING:
    import collections.abc


def split_presenters(p: str) -> list[str]:
    p = p.replace(".", "")  # remove dots from names
    p = re.sub(r"\([^)]*\)", "", p)  # remove stuff between brackets
    p = p.replace(" vd ", " van de ")  # especially for Martijn :-)
    result = list(
        filter(
            lambda s: s,
            map(lambda s: s.strip(), re.split(r"- | -|,|\&+|/| en | and ", p)),
        )
    )
    return result if result else [p]


def create_from_document(
    event: "firestore.DocumentSnapshot",
    session: "firestore.DocumentSnapshot",
    unit: str,
) -> "collections.abc.Generator[Contribution, None, None]":
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
            unit=unit,
            type="xke",
        )


class XkeSource(Source, abc.ABC):
    def __init__(self, sink: "Sink"):
        super().__init__(sink)
        if gcloud_config_helper.on_path():
            credentials, _ = gcloud_config_helper.default()
        else:
            logging.info("using application default credentials")
            credentials, _ = google.auth.default()
        self.db = firestore.Client(credentials=credentials, project="xke-nxt")

    @property
    def name(self):
        return "firestore"

    @property
    @abc.abstractmethod
    def unit(self) -> str:
        raise NotImplementedError()

    @property
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        latest = self.sink.latest_entry(unit=self.unit, contribution="xke")

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
            contributions: list["Contribution"] = []
            for session in (
                self.db.collection("events")
                .document(event.id)
                .collection("sessions-public")
                .where("unit.id", "==", self.unit.upper())
                .stream()
            ):
                for contribution in create_from_document(event, session, self.unit):
                    contributions.append(contribution)

            contributions.sort(key=lambda x: x.date)

            for contribution in contributions:
                if latest < contribution.date < now:
                    yield contribution


class BinxXkeSource(XkeSource):
    @property
    def unit(self) -> str:
        return "binx"


class CloudXkeSource(XkeSource):
    @property
    def unit(self) -> str:
        return "cloud"


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    sink = Sink()
    sink.latest_entry = lambda unit, contribution: datetime.fromordinal(1).replace(
        tzinfo=pytz.utc
    )
    for src in [BinxXkeSource(sink), CloudXkeSource(sink)]:
        for c in src.feed:
            print(c)
