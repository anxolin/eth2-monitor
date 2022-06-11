from operator import le
import requests
import json
import yaml
import config

BATCH_SIZE = 50

base_url = config.config['beacon_chain']['base_url']    

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

if __name__ == '__main__':
    main()