import datetime
import logging
import os

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

CHECK_INTERVAL = datetime.timedelta(seconds=30)
NOTIFICATIONS = [
    {'delta': datetime.timedelta(minutes=60), 'message': "%s will start in about one hour!"},
    {'delta': datetime.timedelta(minutes=15), 'message': "%s will start in 15 minutes."},
    # {'delta': datetime.timedelta(minutes=2), 'message': "%s will start in 2 minutes."},
    {'delta': datetime.timedelta(minutes=1), 'message': "%s is about to start!"}
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! I am F1ScheduleTelegramBot! I am currently mostly hardcoded, but more "
             "features will be coming soon! Your chat id is: `%s`." % update.effective_chat.id,
    )


async def update_callback(context: ContextTypes.DEFAULT_TYPE):
    ical_url = "https://files-f1.motorsportcalendars.com/f1" \
               "-calendar_p1_p2_p3_qualifying_sprint_gp.ics"

    # Get the F1 calendar
    cal = Calendar(requests.get(ical_url).text)
    print(cal.events)

    now = datetime.datetime.now(datetime.timezone.utc)
    chat_id = os.getenv('CHAT_ID')
    for notification in NOTIFICATIONS:
        for event in cal.events:
            event_begin_timedelta = event.begin - notification['delta'] - 0.5 * CHECK_INTERVAL
            event_end_timedelta = event.begin - notification['delta'] + 0.5 * CHECK_INTERVAL
            logging.debug("[%s]: %s -- %s - %s" % (
                event.name,
                notification['message'],
                event_begin_timedelta,
                event_end_timedelta)
            )
            if event_begin_timedelta < now < event_end_timedelta:
                logging.info("Event in notification window!")
                message = notification['message'] % event.name
                logging.info("Sending message: \"%s\" to chat_id: %s." % (message, chat_id))
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                )


async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    event = job.data
    chat_id = job.chat_id
    message = "%s will begin %s" % event.name, event.begin.humanize()
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
    )


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""

    current_jobs = context.job_queue.get_jobs_by_name(name)

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

    chat_id = os.getenv('CHAT_ID')

    for event in cal.events:
        if event.begin > arrow.utcnow() and event.begin - arrow.utcnow().shift(weeks=+1) > arrow.utcnow():
            # For now reschedule all events
            remove_job_if_exists(event.name, context)
            context.job_queue.run_once(send_notifications, (event.begin - arrow.utcnow().shift(minutes=+60)).seconds,
                                       chat_id=chat_id, name=event.name, data=event)
            context.job_queue.run_once(send_notifications, (event.begin - arrow.utcnow().shift(minutes=+15)).seconds,
                                       chat_id=chat_id, name=event.name, data=event)
            context.job_queue.run_once(send_notifications, (event.begin - arrow.utcnow().shift(minutes=+1)).seconds,
                                       chat_id=chat_id, name=event.name, data=event)


def main():
    bot_token = os.getenv('BOT_TOKEN')
    if bot_token is None or len(bot_token) <= 0:
        raise Exception("No BOT_TOKEN in environment!")

    chat_id = os.getenv('CHAT_ID')
    if chat_id is None or len(chat_id) <= 0:
        raise Exception("No CHAT_ID in environment!")

    application = ApplicationBuilder().token(bot_token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    job_queue = application.job_queue
    job_queue.run_repeating(sync_ical, interval=60, first=1)

    application.run_polling()


if __name__ == '__main__':
    main()
