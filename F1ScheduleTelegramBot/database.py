import sqlite3

from consts import DEV_CHAT_NAME


# Retrieves all non-dev chats from the database
def list_chats(conn: sqlite3.connection):
    cur = conn.cursor()
    res = cur.execute("SELECT name, chat_id FROM chats WHERE name!=:name", {"name": DEV_CHAT_NAME})
    rows = res.fetchall()
    cur.close()
    return rows


# Retrieves the dev chat from the database
def get_chat_dev(conn: sqlite3.connection):
    cur = conn.cursor()
    res = cur.execute("SELECT name, chat_id FROM chats WHERE name=:name", {"name": DEV_CHAT_NAME})
    rows = res.fetchall()
    if len(rows) == 0:
        raise Exception("DEV chat id does not exist in database")

    return rows[0]
