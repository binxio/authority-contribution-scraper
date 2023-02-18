import logging
import os
import typing

from authority import AllSources
from authority.sink import Sink

if typing.TYPE_CHECKING:
    from authority.source import Source


class Loader:
    def __init__(self, sink: "Sink", sources: list["Source"]):
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
    sources = [source(sink) for source in AllSources]

    loader = Loader(sink, sources)
    return loader.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    main()
