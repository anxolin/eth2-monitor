from socket import timeout
import backoff
import telegram
import logging
import asyncio
import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# Config
telegram_config = config.config["telegram"]
if telegram_config is not None:
    bot = telegram.Bot(token=telegram_config["access_token"])
    chat_id = telegram_config["channel_id"]
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
