import logging
import os
import sys
import typing
from datetime import datetime

import gcloud_config_helper
import google
import pytz
from google.cloud import bigquery, exceptions
from google.cloud.bigquery.job import QueryJob

from authority.contribution import Contribution, Schema

if typing.TYPE_CHECKING:
    import collections.abc


class Sink:
    def __init__(self):
        if gcloud_config_helper.on_path():
            credentials, project = gcloud_config_helper.default()
        else:
            credentials, project = google.auth.default()

        self.client = bigquery.Client(credentials=credentials, project=project)
        self._table_ref = f"{self.client.project}.authority.contributions"
        self.table = self.create_table_if_not_exists()

    def create_table_if_not_exists(self) -> bigquery.Table:
        table = self.client.create_table(
            table=bigquery.Table(table_ref=self._table_ref, schema=Schema),
            exists_ok=True,
        )
        logging.info("table %s already exists.", table.full_table_id)
        return table

    def latest_entry(self, unit: str, contribution: str) -> datetime:
        """
        returns the latest date of contributions of type `contribution`
        from unit `unit`, or 0001-01-01 if none found.
        """
        last_entry: datetime = datetime.fromordinal(1).replace(tzinfo=pytz.utc)
        job: QueryJob = self.client.query(
            f'SELECT max(date) AS latest '
            f'FROM `{self._table_ref}` '
            f'WHERE type="{contribution}" AND unit = "{unit}"'
        )
        for r in job.result():
            return r[0].replace(tzinfo=pytz.utc) if r[0] else last_entry
        return last_entry

    def load(self, contributions: "collections.abc.Generator[Contribution, None, None]"):
        try:
            result = self.client.insert_rows(
                table=self.table, rows=map(lambda c: c.as_tuple, contributions)
            )
            if result:
                logging.error("failed to add new contributions")
                logging.error("%s", "\n".join(result))
                sys.exit(1)

        except exceptions.BadRequest as e:
            if e.errors[0].get("message") != "No rows present in the request.":
                raise


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    sink = Sink()
