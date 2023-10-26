"""The message_handler module contains the MessageHandler class."""
import abc

# pylint: disable=too-few-public-methods


class MessageHandlerInterface:
    """
    The MessageHandlerInterface is the interface for all implementations of the
    MessageHandler class.
    """

    @abc.abstractmethod
    async def send_telegram_message(
        self, context, chat_id, message, *args, **kwargs
    ):
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
        raise NotImplementedError


class MessageHandler(MessageHandlerInterface):
    """The default message handler implementation to send a telegram message."""

    async def send_telegram_message(
        self, context, chat_id, message, *args, **kwargs
    ):
        return await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            *args,
            **kwargs,
        )
