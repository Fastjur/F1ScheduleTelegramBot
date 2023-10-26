import sqlite3
from dataclasses import dataclass

import arrow
import pytest
from ics import Calendar
from telegram.ext import ContextTypes

from f1_schedule_telegram_bot.ical_fetcher import ICalFetcherInterface
from f1_schedule_telegram_bot.main import F1ScheduleTelegramBot
from f1_schedule_telegram_bot.message_handler import MessageHandlerInterface

pytest_plugins = ("pytest_asyncio",)


@dataclass
class MockMessage:
    context: ContextTypes.DEFAULT_TYPE
    chat_id: int
    message: str


class MockMessageHandler(MessageHandlerInterface):
    async def send_telegram_message(
        self, context, chat_id, message, *args, **kwargs
    ):
        self.messages.append(MockMessage(context, chat_id, message))

    def __init__(self):
        self.messages: list[MockMessage] = []


class MockICalFetcher(ICalFetcherInterface):
    async def fetch(self) -> Calendar:
        with open(
            "f1-calendar_p1_p2_p3_qualifying_sprint_gp.ics",
            "r",
            encoding="UTF-8",
        ) as ics:
            return Calendar(ics.read())


# Set up in memory sqlite3 database
@pytest.fixture(scope="function")
def get_dbconn():
    dbconn = sqlite3.connect(":memory:")
    dbconn.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            type TEXT NOT NULL CHECK (type <> ''),
            name TEXT NOT NULL CHECK (name <> '')
        )
        """
    )
    return dbconn


@pytest.mark.asyncio
async def test_send_weekend_calendar_no_chats(get_dbconn):
    handler = MockMessageHandler()
    dbconn = get_dbconn
    bot = F1ScheduleTelegramBot(
        dbconn=dbconn,
        ergast=None,
        message_handler=handler,
        ical_fetcher=MockICalFetcher(),
    )
    await bot.send_weekend_calendar(None)
    assert not handler.messages


@pytest.mark.asyncio
async def test_send_weekend_calendar_one_chat(get_dbconn):
    handler = MockMessageHandler()
    dbconn = get_dbconn
    dbconn.execute(
        """
        INSERT INTO chats (chat_id, type, name) VALUES (15, 'the_type', 'the_name')
        """
    )
    bot = F1ScheduleTelegramBot(
        dbconn=dbconn,
        ergast=None,
        message_handler=handler,
        ical_fetcher=MockICalFetcher(),
    )

    # Mock the current date by overriding arrow.utcnow
    arrow.utcnow = lambda: arrow.get("2023-10-19T20:00:00+00:00")

    # Note, the context is normally not a string, but a telegram.ext.CallbackContext
    await bot.send_weekend_calendar("the-context")

    expected_message = (
        "<b>United States Grand Prix</b>\n"
        "Qualifying: 23:00\n"
        "Grand Prix: 21:00\n"
    )

    assert handler.messages == [
        MockMessage(
            context="the-context", chat_id=15, message=expected_message
        )
    ]


@pytest.mark.asyncio
async def test_simple_no_event(get_dbconn):
    handler = MockMessageHandler()
    dbconn = get_dbconn
    dbconn.execute(
        """
        INSERT INTO chats (chat_id, type, name) VALUES (15, 'the_type', 'the_name')
        """
    )

    # Mock the current date by overriding arrow.utcnow
    arrow.utcnow = lambda: arrow.get("2023-10-12T20:00:00+00:00")

    bot = F1ScheduleTelegramBot(
        dbconn=dbconn,
        ergast=None,
        message_handler=handler,
        ical_fetcher=MockICalFetcher(),
    )
    await bot.send_weekend_calendar(None)
    assert not handler.messages
