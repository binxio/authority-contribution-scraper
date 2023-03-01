import logging
import re
import typing
from datetime import datetime

import gcloud_config_helper
import google
import pytz
from google.cloud import firestore

from authority.contribution import Contribution
from authority.sources.base_ import Source
from authority.util.unit import get_unit_from_user

if typing.TYPE_CHECKING:
    import collections.abc
    from authority.sink import Sink


def split_presenters(presenter: str) -> list[str]:
    presenter = presenter.replace(".", "")  # remove dots from names
    presenter = re.sub(r"\([^)]*\)", "", presenter)  # remove stuff between brackets
    presenter = presenter.replace(" vd ", " van de ")  # especially for Martijn :-)
    result = list(
        filter(
            lambda s: s,
            map(lambda s: s.strip(), re.split(r"- | -|,|\&+|/| en | and ", presenter)),
        )
    )
    return result if result else [presenter]


class XkeSource(Source):
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
    def contribution_type(self) -> str:
        return "xke"

    @classmethod
    def scraper_id(cls) -> str:
        return "xke.xebia.com"

    @property
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        latest = self.sink.latest_entry(type=self.contribution_type, scraper_id=self.scraper_id())

        logging.info("reading new XKE sessions from firestore since %s", latest)

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
                .stream()
            ):
                for contribution in self.create_contribution_from_xke_document(
                        event=event,
                        session=session,
                        contribution_type=self.contribution_type,
                ):
                    contributions.append(contribution)

            contributions.sort(key=lambda entry: entry.date)

            for contribution in contributions:
                if latest < contribution.date < now:
                    yield contribution

    def create_contribution_from_xke_document(
            self,
            event: "firestore.DocumentSnapshot",
            session: "firestore.DocumentSnapshot",
            contribution_type: str,
    ) -> "collections.abc.Generator[Contribution, None, None]":
        session_dict = session.to_dict()

        if not (start_time := session_dict.get("startTime", None)):
            logging.error("%s - %s - does not have a startTime field", event.id, session.id)
            return

        if not (presenters := session_dict.get("presenter", None)):
            logging.error("%s - %s - does not have a presenter field", event.id, session.id)
            return

        if not (title := session_dict.get("title", None)):
            logging.error("%s - %s - does not have a title field", event.id, session.id)
            return

        url = f"https://xke.xebia.com/event/{event.id}/{session.id}/{session_dict.get('slug', '')}"

        for presenter in split_presenters(presenters):
            ms_user = self._ms_graph_api.get_user_by_display_name(display_name=presenter)
            unit = get_unit_from_user(user=ms_user)
            yield Contribution(
                guid=url,
                title=title,
                author=presenter,
                date=start_time,
                url=url,
                unit=unit,
                scraper_id=self.scraper_id(),
                type=contribution_type,
            )


if __name__ == "__main__":
    from pathlib import Path
    import csv
    import dataclasses
    import os
    from authority.sink import Sink

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    sink = Sink()
    sink.latest_entry = lambda **kwargs: datetime.fromordinal(1).replace(
        tzinfo=pytz.utc
    )
    src = XkeSource(sink=sink)
    with Path("./xke_output.csv").open(mode="w") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(field.name for field in dataclasses.fields(Contribution)))
        writer.writeheader()
        for c in src.feed:
            writer.writerow(dataclasses.asdict(c))
