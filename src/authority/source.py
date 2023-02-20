import abc
import typing

if typing.TYPE_CHECKING:
    import collections.abc

    from authority.contribution import Contribution
    from authority.sink import Sink


class Source(abc.ABC):
    def __init__(self, sink: "Sink"):
        self.count = 0
        self.sink = sink

    @abc.abstractmethod
    @property
    def name(self) -> str:
        raise NotImplementedError()

    @property
    def feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        self.count = 0
        for item in self._feed:
            self.count += 1
            yield item

    @abc.abstractmethod
    @property
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        raise NotImplementedError()
