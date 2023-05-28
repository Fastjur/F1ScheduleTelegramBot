"""Main file for the bot, which sets up all requirements and starts running the main event loop."""
import datetime
import logging
import os
import sqlite3

import arrow
import ergast_py  # type: ignore
import pytz  # type: ignore
import requests
from dotenv import load_dotenv
from ics import Calendar  # type: ignore
from prettytable import PrettyTable
from telegram import Update
import telegram
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler

from f1_schedule_telegram_bot import database
from f1_schedule_telegram_bot.consts import DEV_CHAT_NAME, CHECK_INTERVAL, ICAL_URL
from f1_schedule_telegram_bot.message_handler import send_telegram_message

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

dbconn = sqlite3.connect("f1.db")
e = ergast_py.Ergast()


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    if update.effective_chat is None:
        return

    chat_id = update.effective_chat.id
    logging.info("Received start command from chat_id: %s", chat_id)

    # For private chats, register using the username,
    # otherwise use the group name for identification
    name = ""
    if update.effective_chat.type == telegram.constants.ChatType.PRIVATE:
        name = update.effective_chat.username
    else:
        name = update.effective_chat.title

    try:
        chat = database.get_chat(dbconn, chat_id)
        if chat is None:
            message = (
                "Hello! I am F1ScheduleTelegramBot. I am currently mostly hardcoded, "
                "but more features will be coming soon!\n\n"
                "Your chat has been registered successfully 🏁"
            )
            await send_telegram_message(context, chat_id, message)

            cur = dbconn.cursor()
            cur.execute(
                "INSERT INTO chats VALUES (:chat_id, :type, :name)",
                {
                    "chat_id": chat_id,
                    "type": update.effective_chat.type,
                    "name": name,
                },
            )
            dbconn.commit()
            return

        await send_telegram_message(
            context, chat_id, "Your chat has already been registered! 🚩🚩🚩"
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
        await send_telegram_message(context, chat_id, message)


def remove_job_if_exists(uid: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given uid. Returns whether job was removed."""

    current_jobs = context.job_queue.get_jobs_by_name(uid)

    if not current_jobs:
        return False

    for job in current_jobs:
        job.schedule_removal()

    return True


async def handle_standings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle "standings" command to show the latest standings for Drivers and Constructors."""
    logging.info(
        "Received /standings command from chat_id: %s", update.effective_chat.id
    )

    constructor_standing = e.season().get_constructor_standing()
    driver_standing = e.season().get_driver_standing()
    races = e.season().get_races()

    table = PrettyTable()
    table.field_names = ["Position", "Name", "Team", "Points"]

    message = f"Standing after the {races[driver_standing.round_no - 1].race_name} \n"
    message += "<code>\n"
    message += "Drivers: \n"

    for standing in driver_standing.driver_standings:
        table.add_row(
            [
                standing.position_text,
                f"{standing.driver.given_name} {standing.driver.family_name}",
                standing.constructors[0].name,
                standing.points,
            ]
        )
    message += table.get_string()

    table.clear()
    table.field_names = ["Position", "Team", "Points", "Wins"]

    message += "\n Constructors: \n"
    for standing in constructor_standing.constructor_standings:
        table.add_row(
            [
                standing.position_text,
                standing.constructor.name,
                standing.points,
                f"{standing.wins} / {constructor_standing.round_no}",
            ]
        )
    message += table.get_string()
    message += "</code>"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode=telegram.constants.ParseMode.HTML,
    )


async def fetch_ical() -> Calendar:
    """Retrieve Formula 1 events calendar."""
    try:
        return Calendar(requests.get(ICAL_URL, timeout=30).text)
    except requests.exceptions.Timeout as err:
        raise TimeoutError("timeout of 30s exceeded") from err
    except requests.exceptions.RequestException as err:
        raise SystemExit(
            "A request exception occurred whilst attempting to get ical"
        ) from err


async def send_weekend_calendar(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with the calendar for the current weekend."""
    try:
        cal = await fetch_ical()
    except requests.exceptions.Timeout as err:
        logging.warning(f"unable to get iCal: {err}")
        return

    # Order the events such that the quali is listed before the race
    events = sorted(cal.events)
    utcnow = arrow.utcnow().shift(days=-3)
    message = ""

    for event in events:
        # Get the quali and race for this weekend
        if (
            utcnow < event.begin
            and event.begin <= utcnow.shift(days=4)
            and ("F1: Qualifying" in event.name or "F1: Grand Prix" in event.name)
        ):
            race_name = event.name.split("(")[1].split(")")[0]
            event_name = event.name.split("F1:")[1].split("(")[0].strip()

            # If message is empty, start with the name of the race
            if message == "":
                message += f"<b>{race_name}</b>\n"

            message += f"{event_name}: {event.begin.format('HH:mm')}\n"

    if message == "":
        return

    chats = database.list_chats(dbconn)
    for chat in chats:
        chat_id = chat.chat_id
        await send_telegram_message(
            context,
            chat_id,
            message,
            parse_mode=telegram.constants.ParseMode.HTML,
        )

    return


async def check_rawe_ceek(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notify channels if there is a race this week."""
    try:
        cal = await fetch_ical()
    except requests.exceptions.Timeout as err:
        logging.warning(f"unable to get iCal: {err}")
        return

    utcnow = arrow.utcnow()

    for event in cal.events:
        # Get the first grand prix in the calendar
        if utcnow < event.begin and "F1: Grand Prix" in event.name:
            next_race_name = event.name.split("(")[1].split(")")[0]
            message = ""
            # Check if it's in 7 days
            if event.begin <= utcnow.shift(days=7):
                message = f"""It's rawe ceek!\n\n""" f"""{next_race_name}"""
            else:
                message = f"{next_race_name} is {event.begin.humanize()}"

            chats = database.list_chats(dbconn)
            for chat in chats:
                chat_id = chat.chat_id
                await send_telegram_message(context, chat_id, message)

            return

    # Get the last race and announce offseason
    last_race = sorted(cal.events)[-1]
    # If the last race of the calendar was last weekend
    if utcnow.shift(days=-7) < last_race:
        chats = database.list_chats(dbconn)
        for chat in chats:
            chat_id = chat.chat_id
            await send_telegram_message(context, chat_id, "Welcome to offseason! 🤪")


async def sync_ical(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Synchronize the ical link, store all events in job queue."""
    # Get the F1 calendar

    try:
        cal = await fetch_ical()
    except requests.exceptions.Timeout as err:
        logging.warning(f"unable to get iCal: {err}")
        return

    utcnow = arrow.utcnow()

    for event in cal.events:
        # If the event is cancelled, don't add a job for it.
        if "canceled" in event.name.lower():
            continue
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

    await send_telegram_message(context, chat_dev.chat_id, message)


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

    await send_telegram_message(
        context,
        chat_dev.chat_id,
        message,
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
    standings_handler = CommandHandler("standings", handle_standings)

    schedule_handler = CommandHandler("schedule", handle_list_schedule)
    chats_handler = CommandHandler("chats", handle_list_chats)

    application.add_handlers([start_handler, standings_handler, schedule_handler, chats_handler])

    job_queue = application.job_queue
    job_queue.run_repeating(
        sync_ical, interval=CHECK_INTERVAL, first=1, name="sync_ical"
    )

    job_queue.run_daily(
        check_rawe_ceek,
        time=datetime.time(
            hour=10,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=pytz.timezone("Europe/Amsterdam"),
        ),
        days=(1,),
        name="check_rawe_ceek",
    )

    job_queue.run_daily(
        send_weekend_calendar,
        time=datetime.time(
            hour=20,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=pytz.timezone("Europe/Amsterdam"),
        ),
        days=(4,),
        name="send_weekend_calendar",
    )

    application.run_polling()


if __name__ == "__main__":
    main()
