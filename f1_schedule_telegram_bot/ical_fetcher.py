"""The ical_fetcher module contains the ICalFetcher class."""
import abc

import requests
from ics import Calendar  # type: ignore

from f1_schedule_telegram_bot.consts import ICAL_URL


# pylint: disable=too-few-public-methods


class ICalFetcherInterface:
    """The ICalFetcherInterface class provides an interface for ICalFetcher."""

    @staticmethod
    @abc.abstractmethod
    async def fetch() -> Calendar:
        """Retrieve Formula 1 events calendar."""
        raise NotImplementedError


class ICalFetcher(
    ICalFetcherInterface
):  # pylint: disable=too-few-public-methods
    """
    Production implementation of the ICalFetcherInterface to retrieve the Formula 1 events
    from `f1_schedule_telegram_bot.consts.ICAL_URL`.
    """

    @staticmethod
    async def fetch() -> Calendar:
        """Retrieve Formula 1 events calendar."""
        try:
            return Calendar(requests.get(ICAL_URL, timeout=30).text)
        except requests.exceptions.Timeout as err:
            raise TimeoutError("timeout of 30s exceeded") from err
        except requests.exceptions.RequestException as err:
            raise SystemExit(
                "A request exception occurred whilst attempting to get ical"
            ) from err
