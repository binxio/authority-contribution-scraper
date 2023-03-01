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
        """
        Create a BigQuery table if it doesn't exist

        :return: The authority-contribution-scraper BigQuery table
        :rtype: :obj:`Table <bigquery:google.cloud.bigquery.table.Table>`
        """
        table = self.client.create_table(
            table=bigquery.Table(table_ref=self._table_ref, schema=Schema),
            exists_ok=True,
        )
        logging.info("table %s already exists.", table.full_table_id)
        return table

    def latest_entry(self, **kwargs) -> datetime:
        """
        :param kwargs: Equals filter to use to find the latest entry
\
        :return: returns the latest date of contributions matching the specified filters
        :rtype: :obj:`datetime <datetime.datetime>`
        """
        """
        returns the latest date of contributions of type `contribution`
        from unit `unit`, or 0001-01-01 if none found.
        """
        query_filter = " AND ".join([f"{key}={value}" for key, value in kwargs.items()])

        last_entry: datetime = datetime.fromordinal(1).replace(tzinfo=pytz.utc)
        query_job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("table_ref", "STRING", self._table_ref),
                bigquery.ScalarQueryParameter("query_filter", "INT64", query_filter),
            ]
        )
        job: QueryJob = self.client.query(
            query=f'SELECT max(date) AS latest '
                  f'FROM @table_ref '
                  f'WHERE @query_filter',
            job_config=query_job_config,
        )
        for entry in job.result():
            return entry[0].replace(tzinfo=pytz.utc) if entry[0] else last_entry
        return last_entry

    def load(self, contributions: "collections.abc.Generator[Contribution, None, None]"):
        """
        Loads contributions into the BigQuery table

        :param collections.abc.Generator contributions: The contributions to insert into the BigQuery Table
        """
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
                raise e


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    sink = Sink()
