"""The message_handler module contains functions for handling messages."""


async def send_telegram_message(context, chat_id, message, *args, **kwargs):
    """
    Send a telegram message to chat_id.

    Parameters
    ----------
    context : :class:`telegram.ext.CallbackContext`
        The context of the telegram bot.
    chat_id : int
        The chat id to send the message to.
    message : str
        The message to send.

    See Also
    --------
    :func:`telegram.Chat.send_message`

    """

    return context.bot.send_message(
        chat_id=chat_id,
        text=message,
        *args,
        **kwargs,
    )
