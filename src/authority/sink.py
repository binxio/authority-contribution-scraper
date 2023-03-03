"""
Module containing the Sink class
"""
import logging
import os
import sys
import typing
from datetime import datetime

import gcloud_config_helper
import google
import pytz
from google.cloud import bigquery, exceptions
from google.cloud.bigquery import SqlParameterScalarTypes
from google.cloud.bigquery.job import QueryJob

from authority.model.contribution import Contribution, Schema

if typing.TYPE_CHECKING:
    import collections.abc


class Sink:
    """
    Wrapper for BigQuery to help write contributions to BigQuery
    """
    def __init__(self):
        if gcloud_config_helper.on_path():
            credentials, project = gcloud_config_helper.default()
        else:
            credentials, project = google.auth.default()

        self.client = bigquery.Client(credentials=credentials, project=project)
        self._table_ref = f"{self.client.project}.authority.contributions"
        self.table = self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> bigquery.Table:
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
        returns the latest date of contributions of type `contribution`
        from unit `unit`, or 0001-01-01 if none found.

        :param kwargs: Equals filter to use to find the latest entry

        :return: returns the latest date of contributions matching the specified filters
        :rtype: :obj:`datetime <datetime.datetime>`
        """
        last_entry: datetime = datetime.fromordinal(1).replace(tzinfo=pytz.utc)
        query_parameters = [
            self._get_scalar_parameter(key, value) for key, value in kwargs.items()
        ]
        where_clause = " AND ".join(f"{key} = @{key}" for key in kwargs)
        query_job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
        job: QueryJob = self.client.query(
            query=f'SELECT max(date) AS latest '
                  f'FROM {self._table_ref} '
                  f'WHERE {where_clause}',
            job_config=query_job_config,
        )
        for entry in job.result():
            return entry[0].replace(tzinfo=pytz.utc) if entry[0] else last_entry
        return last_entry

    def load(self, contributions: "collections.abc.Generator[Contribution, None, None]"):
        """
        Loads contributions into the BigQuery table

        :param collections.abc.Generator contributions: The contributions to insert into the
         BigQuery Table
        """
        try:
            result = self.client.insert_rows(
                table=self.table, rows=map(lambda c: c.as_tuple, contributions)
            )
            if result:
                logging.error("failed to add new contributions")
                logging.error("%s", "\n".join(result))
                sys.exit(1)

        except exceptions.BadRequest as exception:
            if exception.errors[0].get("message") != "No rows present in the request.":
                raise exception

    @staticmethod
    def _get_scalar_parameter(key: str, value: typing.Any) -> "bigquery.ScalarQueryParameter":
        type_ = SqlParameterScalarTypes.STRING
        if isinstance(value, datetime):
            type_ = SqlParameterScalarTypes.DATETIME
        return bigquery.ScalarQueryParameter(
            name=key,
            type_=type_,
            value=value,
        )



if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    sink = Sink()
