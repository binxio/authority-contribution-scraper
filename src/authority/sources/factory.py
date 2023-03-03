"""
Module containing the factory for authority contribution sources
"""
import inspect
import typing

if typing.TYPE_CHECKING:
    from authority.sources.base_ import AuthoritySource


class AuthoritySourceFactory:
    """
    Factory to register and retrieve authority sources from
    """
    __registered_authority_sources: dict[str, type["AuthoritySource"]] = {}

    @classmethod
    def register(cls, klass: type["AuthoritySource"]):
        """
        Registers a new source to the factory

        :param type klass: The class to register
        """
        if inspect.isabstract(klass):
            return

        cls.__registered_authority_sources[klass.scraper_id()] = klass

    @classmethod
    def get_all_sources(cls) -> tuple[type["AuthoritySource"]]:
        """
        Returns all sources registered to the factory

        :return: A tuple of classes registered to the factory
        :rtype: :obj:`tuple`
        """
        return tuple(cls.__registered_authority_sources.values())
