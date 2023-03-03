"""
Module containing the Contribution model
"""
import dataclasses
import typing
from datetime import datetime

import pytz
from google.cloud.bigquery import SchemaField

Schema = [
    SchemaField("guid", "STRING", mode="REQUIRED"),
    SchemaField("author", "STRING", mode="REQUIRED"),
    SchemaField("title", "STRING", mode="REQUIRED"),
    SchemaField("date", "DATETIME", mode="REQUIRED"),
    SchemaField("unit", "STRING", mode="REQUIRED"),
    SchemaField("type", "STRING", mode="REQUIRED"),
    SchemaField("scraper_id", "STRING"),
    SchemaField("url", "STRING"),
]


@dataclasses.dataclass
class Contribution:
    """
    Class representing a contribution
    """
    guid: str
    author: str
    date: datetime
    title: str
    unit: str
    type: str
    scraper_id: str
    url: typing.Optional[str] = None

    @property
    def as_tuple(self) -> tuple[typing.Any]:
        """
        Returns a contribution as a tuple

        :return: A tuple representing the contribution
        :rtype: :obj:`tuple`
        """
        return tuple(getattr(self, field.name) for field in Schema)

    @property
    def is_valid(self) -> bool:
        """
        Returns True if the contribution is a valid contribution

        :return: True if the contribution is valid
        :rtype: bool:obj:`bool`
        """
        if all((
            not self.guid,
            self.author,
            self.date,
            self.title,
            self.unit,
            self.type,
        )):
            return False

        if self.date.tzinfo != pytz.utc:
            return False

        return True

    def __str__(self):
        return str(self.as_tuple)
