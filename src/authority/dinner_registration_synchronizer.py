"""
XKE attendee scraper
"""

import logging
from collections import defaultdict
from datetime import datetime
from functools import cache
from typing import Optional

import gcloud_config_helper
import google
import pytz
from google.api_core.retry import Retry
from google.cloud import exceptions
from google.cloud import firestore, bigquery
from google.cloud.bigquery import SchemaField, QueryJob, Table


class DinnerRegistrationSynchronizer:
    """
    Dinner Registrations synchronizer
    """

    def __init__(self):
        if gcloud_config_helper.on_path():
            credentials, project = gcloud_config_helper.default()
        else:
            logging.info("using application default credentials")
            credentials, project = google.auth.default()

        ## the scraper reads directly from the XKE next project
        self.xke_db = firestore.Client(credentials=credentials, project="xke-nxt")
        self.bigquery = bigquery.Client(credentials=credentials, project=project)
        self._table_ref = f"{project}.authority.dinner_registrations"
        self._schema = [
            SchemaField("date", "DATETIME", mode="REQUIRED"),
            SchemaField("building_id", "STRING", mode="REQUIRED"),
            SchemaField("city", "STRING", mode="REQUIRED"),
            SchemaField("dinner_registrations", "INTEGER", mode="REQUIRED"),
        ]
        self.table: Optional[Table] = None

    @cache
    def get_building(self, build_id: str) -> dict:
        return self.xke_db.collection("buildings").document(build_id).get().to_dict()

    def _create_table_if_not_exists(self) -> bigquery.Table:
        """
        Create a BigQuery table if it doesn't exist

        :return: The authority-contribution-scraper BigQuery table
        :rtype: :obj:`Table <bigquery:google.cloud.bigquery.table.Table>`
        """

        table = self.bigquery.create_table(
            table=bigquery.Table(table_ref=self._table_ref, schema=self._schema),
            exists_ok=True,
        )
        logging.info("table %s already exists.", table.full_table_id)
        return table

    def latest(self):
        last_entry: datetime = datetime.fromordinal(1).replace(tzinfo=pytz.utc)
        query_job_config = bigquery.QueryJobConfig()
        job: QueryJob = self.bigquery.query(
            query=f"SELECT max(date) AS latest FROM {self._table_ref}",
            job_config=query_job_config,
        )
        for entry in job.result():
            return entry[0].replace(tzinfo=pytz.utc) if entry[0] else last_entry
        return last_entry

    def sync(self, since: datetime = None):
        self.table = self._create_table_if_not_exists()
        latest = since if since else self.latest()
        today = (
            datetime.now()
            .astimezone(pytz.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        logging.info(
            "reading new XKE dinner registration from firestore since %s", since
        )
        events = (
            self.xke_db.collection("events")
            .where("startTime", ">", latest)
            .order_by("startTime")
        )

        registration_count = defaultdict(lambda: defaultdict(int))

        for event in events.stream(retry=Retry()):
            if event.get("startTime") > today:
                break
            for dinner_registration_reference in (
                self.xke_db.collection("events")
                .document(event.id)
                .collection("dinner-registrations")
                .where("status", "==", "Attending")
                .stream(retry=Retry())
            ):
                dinner_registration = dinner_registration_reference.to_dict()
                if building_id := dinner_registration["buildingId"]:
                    registration_count[event.get("startTime")][building_id] += 1
                else:
                    logging.warning(
                        "skipping dinner registration, no building %s",
                        dinner_registration,
                    )

        rows = []
        for date, building_counts in registration_count.items():
            for building_id, count in building_counts.items():
                building = self.get_building(building_id)
                city = building["city"] if building else "unknown"
                rows.append((date, building_id, city, count))

        self._insert_rows(rows)

    def _insert_rows(self, rows: list[tuple]):
        try:
            logging.info(f"insert {len(rows)} rows into {self._table_ref}")
            result = self.bigquery.insert_rows(table=self.table, rows=rows)

            if result:
                logging.error("failed to add new rows\n%s", "\n".join(result))
                raise Exception("failed to add new rows")
        except exceptions.BadRequest as exception:
            if exception.errors[0].get("message") != "No rows present in the request.":
                raise exception


def main():
    logging.basicConfig(level=logging.INFO)
    synchronizer = DinnerRegistrationSynchronizer()
    synchronizer.sync()


if __name__ == "__main__":
    main()
