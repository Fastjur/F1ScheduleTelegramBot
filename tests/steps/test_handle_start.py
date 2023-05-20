import pytest
from pytest_bdd import given, when, then, scenarios
from telegram import Update

from f1_schedule_telegram_bot.main import handle_start


scenarios("../features/handle_start.feature")


@pytest.fixture
def context():
    return {}


@given(
    "there is an update with an effective_chat_id.id None for the /start command",
)
def update_with_chat_id(context):
    update = Update(update_id=1)
    update._effective_chat = {"id": None}
    context["update"] = update


@when("the bot receives the update")
def bot_receives_update(context):
    update = context["update"]
    handle_start(update, None)


@then("no message is sent")
def no_message_is_sent(context):
    pass
