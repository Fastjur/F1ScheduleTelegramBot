import sqlite3

from consts import DEV_CHAT_NAME


# Retrieves all non-dev chats from the database
def list_chats(conn: sqlite3.Connection):
    cur = conn.cursor()
    res = cur.execute("SELECT chat_id, type, name FROM chats WHERE name!=:name",
                      {"name": DEV_CHAT_NAME})
    rows = res.fetchall()
    cur.close()
    return rows


# Retrieves the dev chat from the database
def get_chat_dev(conn: sqlite3.Connection):
    cur = conn.cursor()
    res = cur.execute("SELECT chat_id, type, name FROM chats WHERE name=:name",
                      {"name": DEV_CHAT_NAME})
    rows = res.fetchall()
    if len(rows) == 0:
        raise Exception("DEV chat id does not exist in database")

    return rows[0]


# Retrieves the dev chat from the database
def get_chat(conn: sqlite3.Connection, id: int):
    cur = conn.cursor()
    res = cur.execute("SELECT chat_id, type, name FROM chats WHERE chat_id=:chat_id",
                      {"chat_id": id})
    rows = res.fetchall()
    if len(rows) == 0:
        raise Exception("Chat id does not exist in database")

    return rows[0]
