"""
Module containing the User model
"""
import dataclasses
import typing

import stringcase


@dataclasses.dataclass
class User:
    """
    Class representing a user as it is returned by the MS Graph API
    """

    id: str
    display_name: str
    mail: str
    department: typing.Optional[str]
    company_name: typing.Optional[str]

    @classmethod
    def from_dict(cls, **kwargs) -> "User":
        """
        Parses a dict to a User object

        :param kwargs: dict to parse
        :return: An instance of a User with the properties in the dict
        :rtype: :obj:`User`
        """
        fields = tuple(field.name for field in dataclasses.fields(cls))
        values = {}
        for key, value in kwargs.items():
            if (_key := stringcase.snakecase(key)) not in fields:
                continue
            values[_key] = value
        return cls(**values)
