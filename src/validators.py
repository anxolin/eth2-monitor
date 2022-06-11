from operator import le
import logging
import time
import requests
import json
import yaml
import config
import time

BATCH_SIZE = 50

base_url = config.config['beacon_chain']['base_url']    

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def get_validators_from_eth1_address(eth1_withdraw_account):
    res = requests.get(f'{base_url}/api/v1/validator/eth1/{eth1_withdraw_account}')
    res_json = res.json()
    return [ validator['validatorindex'] for validator in res_json['data']]


def get_validators_from_public_keys(public_keys):
    validators = []
    for i in range(0, len(public_keys), BATCH_SIZE):
        batch = public_keys[i:i+BATCH_SIZE]
        public_keys_params = ",".join([hex(pub) for pub in batch])
        res = requests.get(f'{base_url}/api/v1/validator/{public_keys_params}')
        res_json = res.json()
        validators_batch = [validator['validatorindex'] for validator in res_json["data"]]
        validators += validators_batch
    
    return validators


def get_validators():
    validators_conf = config.config['validators']
    eth1_withdraw_account = validators_conf['eth1_withdraw_account']
    validators1 = get_validators_from_eth1_address(eth1_withdraw_account) if eth1_withdraw_account is not None else []

    public_keys = validators_conf['public_keys']
    validators2 = get_validators_from_public_keys(public_keys) if public_keys is not None else []

    return validators1 + validators2


def get_validators_state(validators, sleep_time=0.2):
    result = []
    for i in range(0, len(validators), BATCH_SIZE):
        batch = validators[i:i+BATCH_SIZE]
        validators_param = ",".join([str(index) for index in batch])
        res = requests.get(f'{base_url}/dashboard/data/validators?validators={validators_param}')
        res_json = res.json()        

        for data in res_json['data']:
            index = data[1]
            status = data[3]
            # log.info('Validator %s is %s', index, state)
            
            result.append({
                'index': index,
                'status': status
            })

        # Prevent rate limits
        time.sleep(sleep_time)
    return result

def main():
    validators_conf = config.config['validators']

    eth1_withdraw_account = validators_conf['eth1_withdraw_account']
    if eth1_withdraw_account is not None:
        validators = get_validators_from_eth1_address(eth1_withdraw_account)
        print(f'validators for ETH1 Address {eth1_withdraw_account} ({len(validators)}):\n{validators}')

    public_keys = validators_conf['public_keys']
    if public_keys is not None:
        validators = get_validators_from_public_keys(public_keys)
        print(f'validators for the {len(public_keys)} Public Keys: {len(validators)}:\n{validators}')

    states = get_validators_state(validators)
    print(f'States {len(states)}:\n{states}')

if __name__ == '__main__':
    main()