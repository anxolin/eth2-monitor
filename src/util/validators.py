import requests
import util.utils as utils
import time
import traceback
import backoff
import util.prometheus as prometheus

# Config: Beacon chain base url
base_url = utils.config.get("beacon_chain", {}).get("base_url", "https://gnosischa.in")

log = utils.getLog(__name__)


def get_validator_url(index):
    return f"{base_url}/validator/{str(index)}"


@backoff.on_exception(backoff.expo, Exception, max_time=120)
def get_json(path, base_api="/api/v1"):
    prometheus.bc_http_request_counter.inc()

    res = requests.get(f"{base_url}{base_api}{path}")
    result = res.json()
    prometheus.bc_http_request_success_counter.inc()

    return result


def get_validators_from_eth1_address(eth1_withdraw_account):
    res_json = get_json(f"/validator/eth1/{eth1_withdraw_account}")
    return [validator["validatorindex"] for validator in res_json["data"]]


def get_validators_from_public_keys(public_keys):
    validators = []
    for batch in utils.divide_list_in_batches(public_keys):
        public_keys_params = ",".join([hex(pub) for pub in batch])
        api_url = f"/validator/{public_keys_params}"
        res_json = get_json(api_url)

        # Make sure res_json["data"] is an array
        if "data" not in res_json or not isinstance(res_json["data"], list):
            error_message = f'Expected an array for property "data" of GET /{api_url}. API JSON Result: {res_json}'
            raise Exception(error_message)

        # Make sure validators have a "validatorindex" property
        validators_info = res_json["data"]
        if "validatorindex" not in validators_info[0]: 
            error_message = f'Expected an object with property "validatorindex" for the validator items return in "data" property of GET /{api_url}. API JSON Result: {res_json}'
            error_message = f'Error getting validators status from API. The JSON result should contain a property "validatorindex" for each validator {validators_info[0]}'
            raise Exception(error_message)

        validators_batch = [
            validator["validatorindex"] for validator in validators_info
        ]
        validators += validators_batch

    return validators


def get_validators():
    validators_conf = utils.config.get("validators", {})

    # Get validators by withdraw address
    eth1_withdraw_account = validators_conf.get("eth1_withdraw_account", None)
    validators1 = (
        get_validators_from_eth1_address(eth1_withdraw_account)
        if eth1_withdraw_account is not None
        else []
    )

    # Get validators by public keys
    public_keys = validators_conf.get("public_keys", [])
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


def get_validators_state(validators, batch_request_delay=0.2):
    result = []
    for batch in utils.divide_list_in_batches(validators):
        validators_param = ",".join([str(index) for index in batch])
        try:
            # Get the status for the validators
            res_json = get_json(
                f"/validators?validators={validators_param}", base_api="/dashboard/data"
            )

            for data in res_json["data"]:
                index = data[1]
                status = data[3]
                # log.info('Validator %s is %s', index, state)

                result.append({"index": index, "status": status})

            # Prevent rate limits
            time.sleep(batch_request_delay)
        except Exception as e:
            log.error(
                "Error getting validators state: {validators_param}\n",
                traceback.format_exc(),
            )

    return result


def get_validators_effectiveness(validators, batch_request_delay=0.2):
    result = []
    for batch in utils.divide_list_in_batches(validators):
        validators_param = ",".join([str(index) for index in batch])
        try:
            # Get the status for the validators
            # i.e https://gnosischa.in/api/v1/validator/30000/attestationeffectiveness
            res_json = get_json(
                f"/validator/{validators_param}/attestationeffectiveness"
            )

            for data in res_json["data"]:
                index = data["validatorindex"]

                # Get the effectiveness.
                #   - TODO: Re-visit how to get the effectivenes. The API changed, and now they report "attestation_efficiency" instead of "attestation_effectiveness", which has a different values and meaning. For now, i return this value as if it was effectivesss, but this needs to be reviewed
                effectiveness = data["attestation_efficiency"]
                # effectiveness = data["attestation_effectiveness"]

                # log.debug("Validator %s effectiveness is %s", index, effectiveness)
                result.append({"index": index, "effectiveness": effectiveness})

            # Prevent rate limits
            time.sleep(batch_request_delay)
        except Exception as e:
            log.error(
                "Error getting validators effectiveness: {validators_param}\n",
                traceback.format_exc(),
            )

    return result


def main():
    # validators = get_json(f"/validators/queue")
    # print(f"Response:\n{validators}")

    validators_conf = utils.config["validators"]

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
