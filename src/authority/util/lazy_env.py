import os
import typing

if typing.TYPE_CHECKING:
    import collections.abc


def lazy_env(key: str, default: "collections.abc.Callable[[], typing.Any]"):
    if value := os.getenv(key):
        return value
    if callable(default):
        return default()
    return default
