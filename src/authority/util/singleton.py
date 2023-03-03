"""
Module containing the Singleton class helper
"""


class Singleton(type):
    """
    Helper class to easily create parameter-considerate Singleton instances
    """
    _instances: dict[tuple, object] = {}

    def __call__(cls, *args, **kwargs) -> object:
        kwargs_tuple = tuple(kwargs.items())
        instance_key = (cls, args, kwargs_tuple)
        if instance_key not in cls._instances:
            cls._instances[instance_key] = super().__call__(*args, **kwargs)
        return cls._instances[instance_key]
