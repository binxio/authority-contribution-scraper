import logging
import os
from typing import List

from authority import AllSources
from authority.sink import Sink
from authority.source import Source


class Loader(object):
    def __init__(self, sink: Sink, sources: List[Source]):
        self.sources = []
        self.sink = sink
        self.sources = sources

    def run(self):
        results = []
        for source in self.sources:
            logging.info("loading from source %s", source.name)
            result = self.sink.load(source.feed())
            results.append({"name": source.name, "count": source.count})
            if source.count:
                logging.info(
                    "added %d new contributions from %s", source.count, source.name
                )
            else:
                logging.info("no new contributions added from %s", source.name)
        return results


def main():
    sink = Sink()
    sources = [s(sink) for s in AllSources]
    loader = Loader(sink, sources)
    return loader.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    main()
