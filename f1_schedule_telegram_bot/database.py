"""The database module contains functions for interacting with the database."""
import sqlite3
from dataclasses import dataclass
from typing import Optional

from f1_schedule_telegram_bot.consts import DEV_CHAT_NAME


@dataclass
class DatabaseChat:
    """A class representing a chat row in the database table chats."""

    def __init__(self, chat_id: int, chat_type: str, name: str):
        """Initialize the DatabaseChat object."""
        self.chat_id = chat_id
        self.chat_type = chat_type
        self.name = name

    def __repr__(self):
        """Return a string representation of the DatabaseChat object."""
        return f"DatabaseChat(chat_id={self.chat_id}, type={self.chat_type}, name={self.name})"


class NoDevChatException(Exception):
    """Raised when the dev chat is not found in the database."""


# Retrieves all non-dev chats from the database
def list_chats(conn: sqlite3.Connection) -> list[DatabaseChat]:
    """Return a list of all chats in the database, except the dev chat."""
    cur = conn.cursor()
    res = cur.execute(
        "SELECT chat_id, type, name FROM chats WHERE name!=:name",
        {"name": DEV_CHAT_NAME},
    )
    rows = res.fetchall()
    cur.close()
    return list(
        map(
            lambda row: DatabaseChat(chat_id=row[0], chat_type=row[1], name=row[2]),
            rows,
        )
    )


# Retrieves the dev chat from the database
def get_chat_dev(conn: sqlite3.Connection) -> DatabaseChat:
    """Return the dev chat from the database."""
    cur = conn.cursor()
    res = cur.execute(
        "SELECT chat_id, type, name FROM chats WHERE name=:name",
        {"name": DEV_CHAT_NAME},
    )
    rows = res.fetchall()
    if len(rows) == 0:
        raise NoDevChatException("DEV chat id does not exist in database")

    return DatabaseChat(chat_id=rows[0][0], chat_type=rows[0][1], name=rows[0][2])


# Retrieves the dev chat from the database
def get_chat(conn: sqlite3.Connection, chat_id: int) -> Optional[DatabaseChat]:
    """Return the chat with the given chat_id from the database."""
    cur = conn.cursor()
    res = cur.execute(
        "SELECT chat_id, type, name FROM chats WHERE chat_id=:chat_id",
        {"chat_id": chat_id},
    )
    rows = res.fetchall()
    if len(rows) == 0:
        return None

    return DatabaseChat(chat_id=rows[0][0], chat_type=rows[0][1], name=rows[0][2])
