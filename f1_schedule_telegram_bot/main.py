"""Main file for the bot, which sets up all requirements and starts running the main event loop."""
import logging
import os
import sqlite3

import arrow
import requests
from dotenv import load_dotenv
from ics import Calendar  # type: ignore
from telegram import Update
import telegram
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler

from f1_schedule_telegram_bot import database
from f1_schedule_telegram_bot.consts import DEV_CHAT_NAME, CHECK_INTERVAL

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


dbconn = sqlite3.connect("f1.db")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    if update.effective_chat is None:
        return

    chat_id = update.effective_chat.id
    logging.info("Received start command from chat_id: %s", chat_id)

    # For private chats, register using the username,
    # otherwise use the group name for identification
    chatName = ""
    if update.effective_chat.type == telegram.constants.ChatType.PRIVATE:
        chatName = update.effective_chat.username
    else:
        chatName = update.effective_chat.title

    try:
        chat = database.get_chat(dbconn, chat_id)
        if chat is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Hello! I am F1ScheduleTelegramBot. I am currently mostly hardcoded, but more "
                "features will be coming soon!\n\n"
                "Your chat has been registered successfully 🏁",
            )
            return

        cur = dbconn.cursor()
        cur.execute(
            "INSERT INTO chats VALUES (:chat_id, :type, :name)",
            {
                "chat_id": chat_id,
                "type": update.effective_chat.type,
                "name": chatName,
            },
        )
        dbconn.commit()
        await context.bot.send_message(
            chat_id=chat_id, text="Your chat has already been registered! 🚩🚩🚩"
        )
    except Exception as err:
        raise SystemExit(
            "A fatal error occurred while reading from or writing to the database."
        ) from err


async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    """
    Send a notification to all chats in the database.

    The notification content is based on event and message that was stored in the job data.
    """
    job = context.job
    event = job.data

    message = f"{event.name} will begin {event.begin.humanize()}"

    chats = database.list_chats(dbconn)
    for chat in chats:
        chat_id = chat.chat_id
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
    """Synchronize the ical link, store all events in job queue."""
    ical_url = (
        "https://files-f1.motorsportcalendars.com/f1"
        "-calendar_p1_p2_p3_qualifying_sprint_gp.ics"
    )

    # Get the F1 calendar
    try:
        cal = Calendar(requests.get(ical_url, timeout=30).text)
    except requests.exceptions.Timeout:
        logging.warning(
            "Timeout of 30 seconds passed in getting ical, skipping for now"
        )
        return
    except requests.exceptions.RequestException as err:
        raise SystemExit(
            "A request exception occurred whilst attempting to get ical"
        ) from err

    utcnow = arrow.utcnow()

    for event in cal.events:
        # First, check if the event is in the next 7 days
        if utcnow <= event.begin <= utcnow.shift(days=7):
            # For now reschedule all events
            remove_job_if_exists(event.uid, context)
            context.job_queue.run_once(
                send_notifications,
                event.begin.shift(minutes=-60).datetime,
                name=event.uid,
                data=event,
            )
            context.job_queue.run_once(
                send_notifications,
                event.begin.shift(minutes=-15).datetime,
                name=event.uid,
                data=event,
            )
            context.job_queue.run_once(
                send_notifications,
                event.begin.shift(minutes=-5).datetime,
                name=event.uid,
                data=event,
            )


async def handle_list_schedule(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /schedule command."""
    logging.info(
        "Received /schedule command from chat_id: %s", update.effective_chat.id
    )

    chat_dev = database.get_chat_dev(dbconn)

    logging.debug(
        "Chat id dev: %s equals user chat_id: %s",
        chat_dev.chat_id,
        update.effective_chat.id == chat_dev.chat_id,
    )
    if update.effective_message.chat_id != int(chat_dev.chat_id):
        return

    message = "Scheduled jobs: \n"
    for job in context.job_queue.jobs():
        job_name = job.data and job.data.name or job.name or "unknown job name"
        message += f"{job.next_t.strftime('%-d %b, %H:%M:%S')}: {job_name}\n"

    await context.bot.send_message(
        chat_id=chat_dev.chat_id,
        text=message,
    )


async def handle_list_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /chats command."""
    logging.info("Received /chats command from chat_id: %s", update.effective_chat.id)

    chat_dev = database.get_chat_dev(dbconn)

    logging.debug(
        "Chat id dev: %s equals user chat_id: %s",
        chat_dev.chat_id,
        update.effective_chat.id == chat_dev.chat_id,
    )
    if update.effective_message.chat_id != int(chat_dev.chat_id):
        return

    message = "Registered chats: \n"
    for chat in database.list_chats(dbconn):
        message += f"{chat.name} ({chat.chat_type}, <code>{chat.chat_id}</code>)\n"

    await context.bot.send_message(
        chat_id=chat_dev.chat_id,
        text=message,
        parse_mode=telegram.constants.ParseMode.HTML,
    )


def main():
    """
    Start the main event loop for the bot.

    It verifies all required env variables are set, connects to the database and starts up the bots
    main event loop.
    """
    # Read all env variables
    bot_token = os.getenv("BOT_TOKEN")
    if bot_token is None or len(bot_token) <= 0:
        raise EnvironmentError("No BOT_TOKEN in environment!")
    chat_id_dev = os.getenv("CHAT_ID_DEV")
    if chat_id_dev is None or len(chat_id_dev) <= 0:
        raise EnvironmentError("No CHAT_ID_DEV in environment!")

    cur = dbconn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                type TEXT NOT NULL CHECK (type <> ''),
                name TEXT NOT NULL CHECK (name <> '')
                )"""
    )

    # Check whether the DEV chatID exists within the DATABASE, if not, create it
    try:
        database.get_chat_dev(dbconn)
    except database.NoDevChatException as no_dev_chat_exception:
        logging.warning(no_dev_chat_exception)
        logging.warning("No DEV chat found, creating one")
        cur.execute(
            "INSERT INTO chats VALUES (:chat_id, :type, :name)",
            {
                "chat_id": chat_id_dev,
                "type": telegram.constants.ChatType.GROUP,
                "name": DEV_CHAT_NAME,
            },
        )
        dbconn.commit()

    application = ApplicationBuilder().token(bot_token).build()

    start_handler = CommandHandler("start", handle_start)
    schedule_handler = CommandHandler("schedule", handle_list_schedule)
    chats_handler = CommandHandler("chats", handle_list_chats)

    application.add_handler(start_handler)
    application.add_handler(schedule_handler)
    application.add_handler(chats_handler)

    job_queue = application.job_queue
    job_queue.run_repeating(
        sync_ical, interval=CHECK_INTERVAL, first=1, name="sync_ical"
    )

    application.run_polling()


if __name__ == "__main__":
    main()
