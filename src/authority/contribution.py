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
    SchemaField("url", "STRING"),
]


class Contribution:
    def __init__(
        self,
        guid: str,
        author: str,
        date: datetime,
        title: str,
        unit: str,
        type: str,
        url: typing.Optional[str] = None,
    ):
        self.guid = guid
        self.author = author
        self.date = date
        self.title = title
        self.unit = unit
        self.type = type
        self.url = url

    @property
    def as_tuple(self):
        return tuple(getattr(self, field.name) for field in Schema)

    @property
    def is_valid(self) -> bool:
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
