from os import access
import backoff
import telegram
import asyncio
import utils

log = utils.getLog(__name__)

# Config
telegram_config = utils.config.get("telegram", None)
if telegram_config is not None:
    access_token = telegram_config.get("access_token", None)
    chat_id = telegram_config["chat_id"]
    if access_token is not None and chat_id is not None:
        bot = telegram.Bot(token=access_token)
    else:
        log.warn(
            'Telegram Notifications are disabled. Config the "telegram" requires both "access_token" and "chat_id"'
        )
else:
    log.warn(
        'Telegram Notifications are disabled. Config the "telegram" channel to enable them'
    )
    bot = None


@backoff.on_exception(backoff.expo, Exception, max_tries=10)
async def send_message(message, parse_mode="MarkdownV2"):
    if bot is not None:
        async with bot:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)
    else:
        log.info(f"[Message] {message}")


@backoff.on_exception(backoff.expo, Exception, max_tries=10)
async def get_user():
    if bot is not None:
        async with bot:
            return await bot.get_me()
    else:
        return telegram.User(
            id=0, first_name="Mock Logger", username="MessageLogger", is_bot=False
        )


async def main():
    await send_message("Hi there 👋")


if __name__ == "__main__":
    asyncio.run(main())
