"""
Module containing the reusable entrypoint code for testing authority sources
"""

import csv
import dataclasses
import logging
import os

from datetime import datetime
from pathlib import Path

import pytz


from authority.model.contribution import Contribution
from authority.sink import Sink

from authority.sources.base_ import AuthoritySource


def test_source(
    source: type["AuthoritySource"],
    latest_entry: datetime = datetime.fromordinal(1).replace(tzinfo=pytz.utc),
) -> "AuthoritySource":
    """
    Method to test sources from their respective entry points

    :param type[AuthoritySource] source: The source to test

    :return: The tested source
    :rtype: :obj:`AuthoritySource`
    """

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    sink_ = Sink()
    sink_.latest_entry = lambda **kwargs: latest_entry
    src = source(sink=sink_)
    with Path("./xke_output.csv").open(mode="w", encoding="UTF-8") as file:
        fieldnames = tuple(field.name for field in dataclasses.fields(Contribution))
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for contribution in src.feed:
            writer.writerow(dataclasses.asdict(contribution))
    return src
