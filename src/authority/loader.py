import logging
import os
import sys
import traceback
import typing

from authority.sink import Sink
from authority.sources.factory import AuthoritySourceFactory

if typing.TYPE_CHECKING:
    from authority.sources.base_ import Source


class Loader:
    def __init__(self, sink: "Sink", sources: tuple["Source"]):
        self.sources = []
        self.sink = sink
        self.sources = sources

    def run(self):
        results = []
        last_exception = None
        for source in self.sources:
            try:
                results.append(self._process_source(source=source))
            except Exception as exception:
                traceback.print_exception(*sys.exc_info())
                last_exception = exception
        if last_exception:
            raise last_exception
        return results

    def _process_source(self, source: "Source"):
        logging.info("loading from source %s", source.name)
        self.sink.load(source.feed)
        result = {"name": source.name, "count": source.count}
        if source.count:
            logging.info("added %d new contributions from %s", source.count, source.name)
            return
        logging.info("no new contributions added from %s", source.name)
        return result


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
