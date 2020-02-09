import pytz
from google.cloud.bigquery import SchemaField
from datetime import datetime

Schema = [
    SchemaField("guid", "STRING", mode="REQUIRED"),
    SchemaField("author", "STRING", mode="REQUIRED"),
    SchemaField("title", "STRING", mode="REQUIRED"),
    SchemaField("date", "DATETIME", mode="REQUIRED"),
    SchemaField("unit", "STRING", mode="REQUIRED"),
    SchemaField("type", "STRING", mode="REQUIRED"),
    SchemaField("url", "STRING"),
]

class Contribution(object):
    def __init__(self, guid:str, author:str, date:datetime, title:str, unit:str, type:str, url:str=None):
        self.guid: str = guid
        self.author: str = author
        self.date: datetime = date
        self.title: str = title
        self.unit: str = unit
        self.type: str = type
        self.url: str = url

    @property
    def as_tuple(self):
        return tuple(self.__getattribute__(field.name) for field in Schema)

    @property
    def is_valid(self) -> bool:
        if not self.guid and self.author and self.date and self.title and self.unit and self.type:
            return False

        if self.date.tzinfo != pytz.utc:
            return False

        return True

    def __str__(self):
        return str(self.as_tuple)