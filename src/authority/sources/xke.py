"""
Module containing the XKE source class
"""
import logging
import re
import typing
from datetime import datetime
from typing import Dict, List, Optional

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


def _split_presenters(presenter: typing.Union[str, List[Dict]]) -> list[str]:
    """
    Splits the presenters for an XKE session by commonly used words/punctuation
    """
    if isinstance(presenter, list):
       presenters = list(map(lambda p: p['displayName'] if isinstance(p, dict) else _split_single_presenter(p), presenter))
    else:
       presenters = _split_single_presenter(presenter)

    result = []
    for presenter in presenters:
        if isinstance(presenter, str):
            result.append(presenter)
        else:
            result.extend(presenter)
    return result

def _split_single_presenter(presenter: str) -> [str]:
    presenter = presenter.replace(".", "")  # remove dots from names
    presenter = re.sub(r"\([^)]*\)", "", presenter)  # remove stuff between brackets
    presenter = presenter.replace(" vd ", " van de ")  # especially for Martijn :-)
    presenter = re.sub(r"organi[sz]ed\s+by\s*", "", presenter)
    result = list(
        filter(
            lambda s: s,
            map(lambda s: s.strip(), re.split(r"- | -|,|&+|/| en | and ", presenter)),
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
            credentials, project = gcloud_config_helper.default()
        else:
            logging.info("using application default credentials")
            credentials, project = google.auth.default()
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
    ) -> "collections.abc.Generator[Optional[Contribution], None, None]":

        if session.id.endswith('-protected'):
            return None

        session_dict = session.to_dict()

        if not (start_time := session_dict.get("startTime")):
            logging.error(
                "%s - %s - does not have a startTime field", event.id, session.id
            )
            return None

        if not (presenters := session_dict.get("presenter")):
            logging.error(
                "%s - %s - does not have a presenter field", event.id, session.id
            )
            return None

        if not (title := session_dict.get("title")):
            logging.error("%s - %s - does not have a title field", event.id, session.id)
            return None

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
    sink = Sink()
    source = XkeSource(sink)
    sink.load(source.feed)

    # from authority.util.test_source import test_source
    # test_source(source=XkeSource)
