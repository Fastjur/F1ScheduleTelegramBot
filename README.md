# F1 Schedule Telegram Bot
Telegram bot to notify telegram users, groups and channels of upcoming F1 events.

## Installation
1. Install Poetry if you don't have it already. You can install it using pip:

    ```shell
    pip install poetry
    ```

2. Clone this repository:

    ```shell
    git clone https://github.com/Fastjur/F1ScheduleTelegramBot.git
    ```
   or using ssh:
    ```shell
    git clone git@github.com:Fastjur/F1ScheduleTelegramBot.git
   ```

3. Install the project dependencies using Poetry:

    ```shell
    cd F1ScheduleTelegramBot
    poetry install
    ```
   
4. Create a Telegram bot using @BotFather:
   - Search for @BotFather in Telegram and start a conversation with it.
   - Follow the instructions to create a new bot and receive the API token.

5. Create a `.env` file in the root directory of the project by copying the [.env.example](.env.example) file and filling in the required environment variables.

## Usage
You can run the project by executing the following command:

```shell
poetry run main
```
This will run the main script, which will start the bot.

## Contributing
If you want to use the git hooks, you need to configure the githooks directory first, using the following command:

 ```shell
 git config core.hooksPath .githooks
 ```

This will enable all the hooks in the `.githooks` directory.
Ensure that you have activated the virtual environment before committing, otherwise the hooks will not work.
You can activate the virtual environment using the following command:

```shell
poetry shell
```

Alternatively, in some IDEs you can configure the virtual environment to be activated automatically when opening the project.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
