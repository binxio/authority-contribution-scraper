"""
XKE attendee scraper
"""
import collections.abc
import logging
from datetime import datetime

import gcloud_config_helper
import google
import pytz
from google.cloud import firestore
from google.api_core.retry import Retry

from authority.model.contribution import Contribution
from authority.sink import Sink
from authority.sources.base_ import AuthoritySource


class AttendeeSource(AuthoritySource):
    """
    Attendee scrapers
    """
    def __init__(self, sink: Sink):
        super().__init__(sink)
        if gcloud_config_helper.on_path():
            credentials, _ = gcloud_config_helper.default()
        else:
            logging.info("using application default credentials")
            credentials, _ = google.auth.default()

        ## the scraper reads directly from the XKE next project
        self.xke_db = firestore.Client(credentials=credentials, project="xke-nxt")

    @property
    def name(self):
        return "firestore"

    @property
    def _contribution_type(self) -> str:
        return "attendees"

    @classmethod
    def scraper_id(cls) -> str:
        return "attendees.xebia.com"

    @property
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":

        ## There
        latest = self.sink.latest_entry(
            type=self._contribution_type, scraper_id=self.scraper_id()
        )

        logging.info("reading new XKE session attendees from firestore since %s", latest)

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

        for event_reference in events.stream(retry=Retry()):
            for session_reference in (
                    self.xke_db.collection("events")
                            .document(event_reference.id)
                            .collection("sessions-public")
                            .stream(retry=Retry())
            ):
                if session_reference.id.endswith('-protected'):
                    continue

                session = session_reference.to_dict()

                for attendee_reference in (
                self.xke_db.collection("events").document(event_reference.id).collection("sessions-private").document(
                        session_reference.id).collection("attendees").stream(retry=Retry())):
                    attendee = attendee_reference.to_dict()

                    date = session.get('startTime')
                    if date < now:
                        yield Contribution(
                            guid=f"{event_reference.id}/{session_reference.id}/{attendee_reference.id}",
                            title=session.get('title')  ,
                            author=attendee['name'],
                            date=session.get('startTime'),
                            url=f"https://xke.xebia.com/event/{event_reference.id}/{session_reference.id}/{session.get('slug', '')}",
                            scraper_id=self.scraper_id(),
                            type=self._contribution_type
                        )


if __name__ == "__main__":
    sink = Sink()
    source = AttendeeSource(sink)
    sink.load(source.feed)

    # from authority.util.test_source import test_source
    # from datetime import datetime
    #
    # test_source(AttendeeSource, datetime.fromisoformat("2025-07-01").astimezone(pytz.utc))
