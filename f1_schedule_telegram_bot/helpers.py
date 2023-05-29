"""The helpers module contains functions removing simple actions from the main methods."""


# Checks whether the event name indicates a race
def is_race(name: str) -> bool:
    """Check whether the even name is a race."""

    return "F1: Grand Prix".lower() in name.lower()


# Checks whether the event name indicates a qualifying session
def is_qualifying(name: str) -> bool:
    """Check whether the even name is a race."""

    return "F1: Qualifying".lower() in name.lower()
