"""
Module containing helper method for retrieving a unit from a user
"""
import functools
import logging

from authority.model.user import User
from authority.ms_graph_api import MSGraphAPI


@functools.lru_cache(maxsize=None)
def _unit_lookup(unit: str) -> str:
    units = {
        "binx.io": "cloud",
        "oblcc": "cloud",
        "binx": "cloud",
    }
    return units.get(unit.lower(), unit.lower())


def _map_user_to_unit(user: User) -> str:
    """
    Returns the unit name of a given user, defaults to "other"
    """
    unit = user.department if user.department else user.company_name
    return _unit_lookup(unit) if unit else "other"


def get_unit_by_display_name(ms_graph_api: MSGraphAPI, name: str) -> str:
    unit = None

    ms_user = ms_graph_api.get_user_by_display_name(display_name=name)
    if ms_user:
        unit = _map_user_to_unit(user=ms_user)

    if not unit:
        logging.info(
            'Could not determine unit for user %s, defaulting to "other"', name
        )
        unit = "other"

    return unit
