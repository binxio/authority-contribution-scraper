"""
Module containing the Contributors model
"""
import dataclasses
import logging
import typing
import google
from gcloud_config_helper import gcloud_config_helper

import pytz
from google.cloud import bigquery, exceptions
from google.cloud.bigquery import SchemaField

from authority.ms_graph_api import MSGraphAPI
from authority.util.unit import get_unit_by_display_name

Schema = [
    SchemaField("author", "STRING", mode="REQUIRED"),
    SchemaField("unit", "STRING", mode="NULLABLE"),
    SchemaField("github_handle", "STRING", mode="NULLABLE")
]


@dataclasses.dataclass
class Contributor:
    """
    contributors of authority contributions
    """
    author: str
    unit: str
    github_handle: typing.Optional[str]

    @property
    def as_tuple(self) -> tuple[typing.Any, ...]:
        """
        Returns a contributor as a tuple
        """
        return tuple(getattr(self, field.name) for field in Schema)

    @property
    def is_valid(self) -> bool:
        """
        Returns True if the contributor is a valid contributor
        """
        return all(
            (
                not self.author,
                self.unit,
            )
        )

    def __str__(self):
        return str(self.as_tuple)

class Synchronizer:
    """
    sync the contributors from new contributions. Adds the unit too.
    """
    def __init__(self):
        if gcloud_config_helper.on_path():
            credentials, project = gcloud_config_helper.default()
        else:
            credentials, project = google.auth.default()

        self.client = bigquery.Client(credentials=credentials, project=project)
        self._table_ref = f"{self.client.project}.authority.contributors"
        self.table = self._create_table_if_not_exists()
        self._ms_graph_api = MSGraphAPI.get_instance()

    def _create_table_if_not_exists(self) -> bigquery.Table:
        """
        Create a BigQuery table if it doesn't exist
        """
        table = self.client.create_table(
            table=bigquery.Table(table_ref=self._table_ref, schema=Schema),
            exists_ok=True,
        )
        logging.info("table %s already exists.", table.full_table_id)
        return table

    def sync(self):
        """
        add new contributors and determine the associated unit
        """
        try:
            result = self.client.insert_rows(
                table=self.table, rows=map(lambda c: c.as_tuple, self.new_contributors())
            )
            if result:
                logging.error("failed to add new contributors")
                logging.error("%s", "\n".join(result))
                exit(1)

        except exceptions.BadRequest as exception:
            if exception.errors[0].get("message") != "No rows present in the request.":
                raise exception

    def new_contributors(self):
        new_contributors = """
            select DISTINCT c.author
            from  authority.contributions c 
            left outer join authority.contributors a 
            on a.author = c.author 
            where a.author is null
        """
        job = self.client.query(new_contributors)
        for row in job.result():
            author = row.get("author")
            unit = get_unit_by_display_name(self._ms_graph_api, author)
            logging.info("adding %s of unit %s", author, unit)
            yield Contributor(author=author, unit=unit, github_handle=None)


if __name__ == "__main__":
    syncer = Synchronizer()
    syncer.sync()
