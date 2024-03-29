"""
Module containing the XKE source class
"""
import logging
import re
import typing
from datetime import datetime

import gcloud_config_helper
import google
import pytz
from google.cloud import firestore

from authority.model.contribution import Contribution
from authority.sources.base_ import AuthoritySource
from authority.sink import Sink

if typing.TYPE_CHECKING:
    import collections.abc
    from authority.sink import Sink


def _split_presenters(presenter: str) -> list[str]:
    """
    Splits the presenters for an XKE session by commonly used words/punctuation
    """
    presenter = presenter.replace(".", "")  # remove dots from names
    presenter = re.sub(r"\([^)]*\)", "", presenter)  # remove stuff between brackets
    presenter = presenter.replace(" vd ", " van de ")  # especially for Martijn :-)
    presenter = re.sub(r"organi[sz]ed\s+by\s*", "", presenter)
    result = list(
        filter(
            lambda s: s,
            map(lambda s: s.strip(), re.split(r"- | -|,|\&+|/| en | and ", presenter)),
        )
    )
    return result if result else [presenter]


class XkeSource(AuthoritySource):
    """
    XKE scraper implementation
    """

    def __init__(self, sink: "Sink"):
        super().__init__(sink)
        if gcloud_config_helper.on_path():
            credentials, _ = gcloud_config_helper.default()
        else:
            logging.info("using application default credentials")
            credentials, _ = google.auth.default()
        self.xke_db = firestore.Client(credentials=credentials, project="xke-nxt")

    @property
    def name(self):
        return "firestore"

    @property
    def _contribution_type(self) -> str:
        return "xke"

    @classmethod
    def scraper_id(cls) -> str:
        return "xke.xebia.com"

    @property
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        latest = self.sink.latest_entry(
            type=self._contribution_type, scraper_id=self.scraper_id()
        )

        logging.info("reading new XKE sessions from firestore since %s", latest)

        now = datetime.now().astimezone(pytz.utc)
        events = (
            self.xke_db.collection("events")
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
                self.xke_db.collection("events")
                .document(event.id)
                .collection("sessions-public")
                .stream()
            ):
                for contribution in self._create_contribution_from_xke_document(
                    event=event,
                    session=session,
                    contribution_type=self._contribution_type,
                ):
                    contributions.append(contribution)

            contributions.sort(key=lambda entry: entry.date)

            for contribution in contributions:
                if latest < contribution.date < now:
                    yield contribution

    def _create_contribution_from_xke_document(
        self,
        event: "firestore.DocumentSnapshot",
        session: "firestore.DocumentSnapshot",
        contribution_type: str,
    ) -> "collections.abc.Generator[Contribution, None, None]":

        if session.id.endswith('-protected'):
            return None

        session_dict = session.to_dict()

        if not (start_time := session_dict.get("startTime", None)):
            logging.error(
                "%s - %s - does not have a startTime field", event.id, session.id
            )
            return

        if not (presenters := session_dict.get("presenter", None)):
            logging.error(
                "%s - %s - does not have a presenter field", event.id, session.id
            )
            return

        if not (title := session_dict.get("title", None)):
            logging.error("%s - %s - does not have a title field", event.id, session.id)
            return

        url = f"https://xke.xebia.com/event/{event.id}/{session.id}/{session_dict.get('slug', '')}"

        for presenter in _split_presenters(presenters):
            yield Contribution(
                guid=url,
                title=title,
                author=presenter,
                date=start_time,
                url=url,
                scraper_id=self.scraper_id(),
                type=contribution_type,
            )


if __name__ == "__main__":
    from authority.util.test_source import test_source
    sink = Sink()
    source = XkeSource(sink)
    sink.load(source.feed)

    # test_source(source=XkeSource)
