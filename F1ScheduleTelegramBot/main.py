import datetime
import logging
import os
import sqlite3

import arrow
import requests
from dotenv import load_dotenv
from ics import Calendar
from telegram import Update
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler

"""
Load .env variables
"""
load_dotenv()

"""
Setup logger
"""
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

CHECK_INTERVAL = datetime.timedelta(minutes=60)
DEV_CHAT_NAME = "DEV"

dbconn = sqlite3.connect('f1.db')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Received start command from user: {}".format(update.effective_chat.id))
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! I am F1ScheduleTelegramBot! I am currently mostly hardcoded, but more "
             "features will be coming soon! Your chat id is: `{}`".format(update.effective_chat.id),
    )


async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    event = job.data
    chat_id = job.chat_id
    message = "{} will begin {}".format(event.name, event.begin.humanize())
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
    )


def remove_job_if_exists(uid: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given uid. Returns whether job was removed."""

    current_jobs = context.job_queue.get_jobs_by_name(uid)

    if not current_jobs:
        return False

    for job in current_jobs:
        job.schedule_removal()

    return True


async def sync_ical(context: ContextTypes.DEFAULT_TYPE) -> None:
    ical_url = "https://files-f1.motorsportcalendars.com/f1" \
               "-calendar_p1_p2_p3_qualifying_sprint_gp.ics"

    # Get the F1 calendar
    cal = Calendar(requests.get(ical_url).text)

    chats = list_chats()
    if len(chats) != 1:
        raise Exception("Expected only 1 non-dev chat to exist")

    chat_id = chats[0][1]

    utcnow = arrow.utcnow()
    for event in cal.events:
        # First, check if the event is in the next 7 days
        if utcnow <= event.begin <= utcnow.shift(days=7):
            # For now reschedule all events
            remove_job_if_exists(event.uid, context)
            context.job_queue.run_once(
                send_notifications,
                event.begin.shift(minutes=-60).datetime,
                chat_id=chat_id,
                name=event.uid,
                data=event
            )
            context.job_queue.run_once(
                send_notifications,
                event.begin.shift(minutes=-15).datetime,
                chat_id=chat_id,
                name=event.uid,
                data=event
            )
            context.job_queue.run_once(
                send_notifications,
                event.begin.shift(minutes=-5).datetime,
                chat_id=chat_id, name=event.uid, data=event
            )


async def list_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Received schedule command from user: {}".format(update.effective_chat.id))

    chat_dev = get_chat_dev()

    logging.debug("Chat id dev: {} equals user chat_id: {}".format(
        chat_dev[1],
        update.effective_chat.id == chat_dev[1])
    )
    if update.effective_message.chat_id != int(chat_dev[1]):
        return

    message = "Scheduled jobs: \n"
    for job in context.job_queue.jobs():
        job_name = job.data and job.data.name or job.name or 'unknown job name'
        message += "{}: {}\n".format(job.next_t.strftime("%-d %b, %H:%M:%S"), job_name)

    await context.bot.send_message(
        chat_id=chat_dev[1],
        text=message,
    )


# Retrieves all non-dev chats from the database
def list_chats():
    cur = dbconn.cursor()
    res = cur.execute("SELECT name, chat_id FROM chats WHERE name!=:name", {"name": DEV_CHAT_NAME})
    rows = res.fetchall()
    cur.close()
    return rows


# Retrieves the dev chat from the database
def get_chat_dev():
    cur = dbconn.cursor()
    res = cur.execute("SELECT name, chat_id FROM chats WHERE name=:name", {"name": DEV_CHAT_NAME})
    rows = res.fetchall()
    if len(rows) == 0:
        raise Exception("DEV chat id does not exist in database")

    return rows[0]


def main():
    bot_token = os.getenv('BOT_TOKEN')
    if bot_token is None or len(bot_token) <= 0:
        raise Exception("No BOT_TOKEN in environment!")

    chat_id = os.getenv('CHAT_ID')
    if chat_id is None or len(chat_id) <= 0:
        raise Exception("No CHAT_ID in environment!")

    chat_id_dev = os.getenv('CHAT_ID_DEV')
    if chat_id_dev is None or len(chat_id_dev) <= 0:
        raise Exception("No CHAT_ID_DEV in environment!")

    cur = dbconn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS chats(name, chat_id)")

    # Check whether the DEV chatID exists within the DATABASE, if not, create it
    try:
        get_chat_dev()
    except Exception as e:
        print(e)
        cur.execute("INSERT INTO chats VALUES (:name, :chat_id)",
                    {"name": DEV_CHAT_NAME, "chat_id": chat_id_dev})
        dbconn.commit()

    # Check whether the chatID exists within the DATABASE, if not, create it
    chats = list_chats()
    if len(chats) == 0:
        cur.execute("INSERT INTO chats VALUES (:name, :chat_id)",
                    {"name": "CHAT", "chat_id": chat_id})
        dbconn.commit()

    application = ApplicationBuilder().token(bot_token).build()

    start_handler = CommandHandler('start', start)
    schedule_handler = CommandHandler('schedule', list_schedule)

    application.add_handler(start_handler)
    application.add_handler(schedule_handler)

    job_queue = application.job_queue
    job_queue.run_repeating(sync_ical, interval=CHECK_INTERVAL, first=1, name="sync_ical")

    application.run_polling()


if __name__ == '__main__':
    main()
