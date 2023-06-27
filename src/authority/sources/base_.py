"""
Module containing the AuthoritySource base class
"""
import abc
import typing

from authority.ms_graph_api import MSGraphAPI
from authority.sources.factory import AuthoritySourceFactory
from authority.util.google_secrets import SecretManager
from authority.util.lazy_env import lazy_env

if typing.TYPE_CHECKING:
    import collections.abc

    from authority.model.contribution import Contribution
    from authority.sink import Sink


class AuthoritySource(abc.ABC):
    """
    Base class for authority scrapers
    """

    def __init__(self, sink: "Sink"):
        """
        :param Sink sink: Sink to retrieve the latest entry from
        """
        self.count = 0
        self.sink = sink

    def __init_subclass__(cls, **kwargs):
        AuthoritySourceFactory.register(cls)

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Returns the display name of the source

        :return: The display name of the source
        :rtype: :obj:`str`
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def _contribution_type(self) -> str:
        raise NotImplementedError()

    @property
    def feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        """
        Returns a generator of the contributions from the current source

        :return: A generator of the contributions from the current source
        :rtype: :obj:`collections.abc.Generator`
        """
        for count, contribution in enumerate(self._feed, start=1):
            self.count = count
            yield contribution

    @property
    @abc.abstractmethod
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def scraper_id(cls) -> str:
        """
        The unique id of the source scraper

        :return: A unique id of the source scraper
        :rtype: :obj:`str`
        """
        raise NotImplementedError()
