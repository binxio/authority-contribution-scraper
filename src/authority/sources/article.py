"""
Module containing the articles source class
"""
import logging
import typing
from datetime import datetime
from time import mktime

import feedparser
import pytz
import requests
from dateutil.parser import parse as datetime_parse

from authority.model.contribution import Contribution
from authority.sources import BlogSource
from authority.sources.base_ import AuthoritySource

if typing.TYPE_CHECKING:
    import collections.abc


class ArticleSource(BlogSource):
    """
    Articles scraper implementation
    """

    def __init__(self, sink):
        super().__init__(sink)
        self.wp_type = "articles"

    @property
    def name(self) -> str:
        return "articles.xebia.com"

    @classmethod
    def scraper_id(cls) -> str:
        return "articles.xebia.com"

    @property
    def _contribution_type(self) -> str:
        return "blog"

if __name__ == "__main__":
    from authority.util.test_source import test_source

    test_source(source=ArticleSource)
