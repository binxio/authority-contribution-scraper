from typing import Iterator
from authority.contribution import Contribution
from authority.sink import Sink


class Source(object):
    def __init__(self, sink):
        self.count = 0
        self.name = ""
        self.sink = sink

    @property
    def feed(self) -> Iterator[Contribution]:
        return None
