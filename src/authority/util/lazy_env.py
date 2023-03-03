"""
Module containing the lazy_env helper for lazily falling back to the default value
"""
import os
import typing

if typing.TYPE_CHECKING:
    import collections.abc


def lazy_env(
        key: str,
        default: "collections.abc.Callable[[], typing.Any] | typing.Any",
) -> typing.Any:
    """
    Retrieves a variable from the environment. When the environment variable has
    not been set this method determines if the default is a callable. If default
    is a callable the result of the call will be returned, if not, default will be returned.

    :param str key: The key of the environment variable to retrieve
    :param collections.abc.Callable | typing.Any default: The default value to use if the
     environment variable has not been set. Can be a callable or any other type

    :return: The value of the environment variable or the default if the
     environment variable has not been set
    :rtype: :obj:`Any<typing.Any>`
    """
    if value := os.getenv(key):
        return value
    if callable(default):
        return default()
    return default
