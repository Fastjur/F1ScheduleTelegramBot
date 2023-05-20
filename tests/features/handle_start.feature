Feature: When the bot receives the /start command, it will send a welcome message to the user.
  As a user, I want to receive a welcome message when I start the bot, so that I know that the bot is working.

  Scenario: The bot receives the /start command with an empty chat_id
    Given there is an update with an effective_chat_id.id None for the /start command
    When the bot receives the update
    Then no message is sent