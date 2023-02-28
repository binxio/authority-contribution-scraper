import abc
import os
import typing

from authority.google_secrets import SecretManager
from authority.ms_graph_api import MSGraphAPI

if typing.TYPE_CHECKING:
    import collections.abc

    from authority.contribution import Contribution
    from authority.sink import Sink


class Source(abc.ABC):
    def __init__(self, sink: "Sink"):
        self.count = 0
        self.sink = sink
        self._ms_graph_api = MSGraphAPI(
            client_id=os.getenv(
                "MS_GRAPH_CLIENT_ID",
                SecretManager().get_secret(
                    "authority-contribution-scraper-ms-graph-client-id"
                ),
            ),
            tenant_id=os.getenv(
                "MS_GRAPH_TENANT_ID",
                SecretManager().get_secret(
                    "authority-contribution-scraper-ms-graph-tenant-id"
                ),
            ),
            client_secret=os.getenv(
                "MS_GRAPH_CLIENT_SECRET",
                SecretManager().get_secret(
                    "authority-contribution-scraper-ms-graph-client-secret"
                ),
            ),
        )

    def __init_subclass__(cls, **kwargs):
        from authority.sources.factory import AuthoritySourceFactory
        AuthoritySourceFactory.register(cls)

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def contribution_type(self) -> str:
        raise NotImplementedError()

    @property
    def feed(self) -> "collections.abc.Generator[Contribution, None, None]":
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
        raise NotImplementedError()
