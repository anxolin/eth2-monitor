import logging
import requests
import config
import backoff

base_url = config.config['beacon_chain']['base_url']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


@backoff.on_exception(backoff.expo, Exception, max_time=120)
def get_json(path, base_api = '/api/v1'):
    res = requests.get(f'{base_url}{base_api}{path}')
    return res.json()

def main():
    validators = get_json(f'/validators/queue')
    print(f'Response:\n{validators}')

if __name__ == '__main__':
    main()