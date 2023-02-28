import inspect
import typing

if typing.TYPE_CHECKING:
    from authority.sources._base import Source


class AuthoritySourceFactory:
    __registered_authority_sources: dict[str, type["Source"]] = dict()

    @classmethod
    def register(cls, klass: type["Source"]):
        if inspect.isabstract(klass):
            return

        cls.__registered_authority_sources[klass.scraper_id()] = klass

    @classmethod
    def get_all_sources(cls) -> tuple[type["Source"]]:
        return tuple(cls.__registered_authority_sources.values())
