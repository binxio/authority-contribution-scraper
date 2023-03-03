"""
Module containing helper method for retrieving a unit from a user
"""
import functools
import typing

if typing.TYPE_CHECKING:
    from authority.model.user import User


@functools.lru_cache(maxsize=None)
def _unit_lookup(unit: str) -> str:
    units = {
        "binx.io": "cloud",
        "oblcc": "cloud",
        "binx": "cloud",
    }
    unit_lower = unit.lower()
    if unit_lower in units:
        return units[unit_lower]
    return unit_lower


def get_unit_from_user(user: "User") -> typing.Optional[str]:
    """
    Returns the unit name of a given user

    :param User user: The user of whom to return the unit for

    :return: The unit name of the given user
    :rtype: str
    """
    if not user:
        return None
    unit = user.company_name
    if department := user.department:
        unit = department
    if unit:
        return _unit_lookup(unit=unit)
    return None
