"""
XKE attendee scraper
"""
import collections.abc
import logging

import gcloud_config_helper
import google
import pytz
from google.cloud import firestore

from authority.model.contribution import Contribution
from authority.sink import Sink
from authority.sources.base_ import AuthoritySource


class AttendeeSink(Sink):
    def __init__(self):
        super().__init__(self, table_name="authority.attendees")


class AttendeeSource(AuthoritySource):
    """
    Attendee scrapers
    """
    def __init__(self, sink: AttendeeSink):
        assert isinstance(sink, AttendeeSink), "sink must be an AttendeeSink"

        super().__init__(sink)
        if gcloud_config_helper.on_path():
            credentials, project = gcloud_config_helper.default()
        else:
            logging.info("using application default credentials")
            credentials, project = google.auth.default()

        self.client = firestore.Client(credentials=credentials, project=project)

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

        for event_reference in events.stream():
            event = event_reference.to_dict()
            attendees = []
            if event['endTime'] > datetime(2025, 1, 1, tzinfo=pytz.utc):
                return

            for session_reference in (
                    self.xke_db.collection("events")
                            .document(event_reference.id)
                            .collection("sessions-public")
                            .stream()
            ):
                if session_reference.id.endswith('-protected'):
                    continue

                session = session_reference.to_dict()

                for attendee_reference in (
                self.xke_db.collection("events").document(event_reference.id).collection("sessions-private").document(
                        session_reference.id).collection("attendees").stream()):
                    attendee = attendee_reference.to_dict()

                    date = session.get('startTime')
                    if date < now:
                        yield Contribution(
                            guid=f"{event_reference.id}/{session_reference.id}/{attendee_reference.id}",
                            title=session.get('title'),
                            author=attendee['name'],
                            date=session.get('startTime'),
                            url=f"https://xke.xebia.com/event/{event_reference.id}/{session_reference.id}/{session.get('slug', '')}",
                            scraper_id=self.scraper_id(),
                            type=self._contribution_type
                        )


if __name__ == "__main__":
    from authority.util.test_source import test_json_source
    from datetime import datetime

    test_json_source(AttendeeSource, datetime.fromisoformat("2024-08-31").astimezone(pytz.utc))
