import logging
import time
import api
import config
import time
import traceback

BATCH_SIZE = 50

base_url = config.config["beacon_chain"]["base_url"]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


def get_validators_from_eth1_address(eth1_withdraw_account):
    res_json = api.get_json(f"/validator/eth1/{eth1_withdraw_account}")
    return [validator["validatorindex"] for validator in res_json["data"]]


def get_validators_from_public_keys(public_keys):
    validators = []
    for i in range(0, len(public_keys), BATCH_SIZE):
        batch = public_keys[i : i + BATCH_SIZE]
        public_keys_params = ",".join([hex(pub) for pub in batch])
        res_json = api.get_json(f"/validator/{public_keys_params}")
        validators_batch = [
            validator["validatorindex"] for validator in res_json["data"]
        ]
        validators += validators_batch

    return validators


def get_validators():
    validators_conf = config.config["validators"]
    eth1_withdraw_account = validators_conf["eth1_withdraw_account"]
    validators1 = (
        get_validators_from_eth1_address(eth1_withdraw_account)
        if eth1_withdraw_account is not None
        else []
    )

    public_keys = validators_conf["public_keys"]
    validators2 = (
        get_validators_from_public_keys(public_keys) if public_keys is not None else []
    )

    # Return unique validators
    unique_validators = set(validators1)
    unique_validators.update(validators2)
    result = list(unique_validators)

    # Sort validators
    #   There's no really a strong need to sort, but messages is nice the validators are sorted in the notifications
    #   Make it easier to spot patterns
    result.sort()
    return result


def get_validators_state(validators, sleep_time=0.2):
    result = []
    for i in range(0, len(validators), BATCH_SIZE):
        batch = validators[i : i + BATCH_SIZE]
        validators_param = ",".join([str(index) for index in batch])
        try:
            # Get the status for the validators
            res_json = api.get_json(
                f"/validators?validators={validators_param}", base_api="/dashboard/data"
            )

            for data in res_json["data"]:
                index = data[1]
                status = data[3]
                # log.info('Validator %s is %s', index, state)

                result.append({"index": index, "status": status})

            # Prevent rate limits
            time.sleep(sleep_time)
        except Exception as e:
            log.error(
                "Error getting info for validators: {validators_param}\n",
                traceback.format_exc(),
            )
    return result


def main():
    validators_conf = config.config["validators"]

    eth1_withdraw_account = validators_conf["eth1_withdraw_account"]
    if eth1_withdraw_account is not None:
        validators = get_validators_from_eth1_address(eth1_withdraw_account)
        print(
            f"validators for ETH1 Address {eth1_withdraw_account} ({len(validators)}):\n{validators}"
        )

    public_keys = validators_conf["public_keys"]
    if public_keys is not None:
        validators = get_validators_from_public_keys(public_keys)
        print(
            f"validators for the {len(public_keys)} Public Keys: {len(validators)}:\n{validators}"
        )

    states = get_validators_state(validators)
    print(f"States {len(states)}:\n{states}")


if __name__ == "__main__":
    main()
