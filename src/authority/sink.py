import logging
import os
from datetime import datetime
from typing import Iterator

import pytz
from google.cloud import bigquery, exceptions
from google.cloud.bigquery.job import QueryJob

from authority.contribution import Contribution, Schema


class Sink(object):
    def __init__(self):
        self.client = bigquery.Client()
        self.create_table_if_not_exists()

    def create_table_if_not_exists(self):
        try:
            self.table = self.client.get_table("authority.contributions")
            logging.info("table {} already exists.".format(self.table.full_table_id))
        except exceptions.NotFound:
            name = f"{self.client.project}.authority.contributions"
            self.table = self.client.create_table(bigquery.Table(name, schema=Schema))
            logging.info("table {} created.".format(self.table.full_table_id))

    def latest_entry(self, unit: str, contribution: str) -> datetime:
        """
        returns the latest date of contributions of type `contribution` from unit `unit`, or 0001-01-01 if none
        found.
        """
        last_entry: datetime = datetime.fromordinal(1).replace(tzinfo=pytz.utc)
        job: QueryJob = self.client.query(
            f'SELECT max(date) as latest FROM `authority.contributions` WHERE type="{contribution}" and unit = "{unit}"'
        )
        for r in job.result():
            return r[0].replace(tzinfo=pytz.utc) if r[0] else last_entry
        return last_entry

    def load(self, contributions: Iterator[Contribution]):
        try:
            result = self.client.insert_rows(
                table=self.table, rows=map(lambda c: c.as_tuple, contributions)
            )
            if result:
                logging.error(
                    "failed to add %s new contributions", len(result), self.count
                )
                logging.error("%s", "\n".join(result))
                exit(1)

        except exceptions.BadRequest as e:
            if e.errors[0].get("message") != "No rows present in the request.":
                raise


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    sink = Sink()
