import requests
import telegram
import time
import json
import logging
import atexit
import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

validator_url = config['validator_url']
validator_active = {}

@atexit.register
def say_goodbye():
    bot = telegram.Bot(token=config['TELEGRAM']['ACCESS_TOKEN'])
    bot.sendMessage(chat_id=config['CHAT']['ID'], text=f'Validator monitor leave, bye~')

if __name__ == '__main__':
    # print(config['TELEGRAM']['ACCESS_TOKEN'])
    bot = telegram.Bot(token=config['TELEGRAM']['ACCESS_TOKEN'])
    bot.sendMessage(chat_id=config['CHAT']['ID'], text=f"`Validator` monitor *start*\n```{json.dumps(validator_url, indent=2)}```", parse_mode='MarkdownV2')
    while True:
        for url in validator_url:
            res = requests.get(url)
            try:
                res_json = res.json()
            except json.decoder.JSONDecodeError:
                log.exception(res.text)
                continue
            try:
                for data in res_json['data']:
                    log.info('%s, %s',data[1], data[3])
                    index = data[1] # == k
                    state = data[3]
                    if (state == 'active_online') == validator_active.get(index, True):
                        continue
                    message = f'<b>{index}</b> change to {state}'
                    message = message.replace('active_online', 'active_online👍')
                    message = message.replace('active_offline', 'active_offline🗿')
                    bot.send_message(chat_id=config['CHAT']['ID'], text=message, parse_mode='HTML')
                    validator_active[index] = not validator_active.get(index, True)
            except IndexError:
                log.exception(res.text)
                continue
        time.sleep(5)