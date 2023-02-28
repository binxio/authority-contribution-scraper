import logging
import os
import typing

from authority.sink import Sink
from authority.sources.factory import AuthoritySourceFactory

if typing.TYPE_CHECKING:
    from authority.sources._base import Source


class Loader:
    def __init__(self, sink: "Sink", sources: tuple["Source"]):
        self.sources = []
        self.sink = sink
        self.sources = sources

    def run(self):
        results = []
        for source in self.sources:
            logging.info("loading from source %s", source.name)
            self.sink.load(source.feed)
            results.append({"name": source.name, "count": source.count})
            if source.count:
                logging.info("added %d new contributions from %s", source.count, source.name)
                continue
            logging.info("no new contributions added from %s", source.name)
        return results


def main():
    sink = Sink()
    sources = tuple(source(sink) for source in AuthoritySourceFactory.get_all_sources())

    loader = Loader(sink, sources)
    return loader.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    main()
