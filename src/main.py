import telegram
import logging
import yaml
import asyncio
import signal
import requests
import time
import json
import os
import sys
from threading import Event


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

validator_url = config['validator_url']
validator_active = {}

# loop = asyncio.get_event_loop()
bot = telegram.Bot(
    token=config['TELEGRAM']['ACCESS_TOKEN']
)
exit = Event()
wait = None

# Config
chat_id = chat_id=config['CHAT']['ID']

async def send_message(message, parse_mode='MarkdownV2'):
    async with bot:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=parse_mode
        )

async def main():
    global wait

    async with bot:
        user = await bot.get_me()
        log.info('[%s] Telegram bot "%s" up', user.username, user.first_name)
        await send_message(f"☀️ Validator Monitor *RESTARTED*")


    while not exit.is_set():
        # for url in validator_url:
        #     res = requests.get(url)
        #     try:
        #         res_json = res.json()
        #     except json.decoder.JSONDecodeError:
        #         log.exception(res.text)
        #         continue
        #     try:
        #         for data in res_json['data']:
        #             log.info('%s, %s',data[1], data[3])
        #             index = data[1] # == k
        #             state = data[3]
        #             if (state == 'active_online') == validator_active.get(index, True):
        #                 continue
        #             message = f'<b>{index}</b> change to {state}'
        #             message = message.replace('active_online', 'active_online👍')
        #             message = message.replace('active_offline', 'active_offline🗿')
        #             await send_message(message, parse_mode='HTML')
        #             validator_active[index] = not validator_active.get(index, True)
        #     except IndexError:
        #         log.exception(res.text)
        #         continue
        
        exit.wait(5)


async def say_goodbye():    
    async with bot:
        await send_message(f"💤 Validator Monitor *SHUTDOWN*\. Have a nice day Ser\!")
    log.info("Have a good day Ser!")


def stop(signal_number=None, _stack=None):
    log.info("Shutting down (Signal=%s)", signal_number)
    exit.set()

if __name__ == '__main__':
    for sig in ('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), stop)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # pragma: no branch
        pass
    finally:
        asyncio.run(say_goodbye())