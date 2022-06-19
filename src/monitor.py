import validators
import messages
import prometheus
import utils

log = utils.getLog(__name__)

STATUS_LABELS = {"active_online": "*ONLINE* 👍", "active_offline": "*OFFLINE* 🔥"}


class ValidatorMonitor:
    """
    Monitors a set of validators
    """

    def __init__(self, monitored_validators, batch_request_delay):
        # State
        self.validator_active = {}
        self.monitored_validators = monitored_validators
        self.batch_request_delay = batch_request_delay

    @prometheus.VALIDATOR_CHECK_TIME.time()
    async def check(self):
        log.debug("Check and Update the state for Validators")

        validators_change_state = {}
        validators_state = validators.get_validators_state(
            validators=self.monitored_validators,
            batch_request_delay=self.batch_request_delay,
        )
        for validator_state in validators_state:
            index = validator_state["index"]
            status = validator_state["status"]
            previous_status = self.validator_active.get(index, True)

            if (status == "active_online") == previous_status:
                # No change in the status from last check
                continue

            # Change the status for the validator
            is_online = not previous_status
            self.validator_active[index] = is_online

            # Get the label for the new state
            new_state = (
                STATUS_LABELS[status] if status in STATUS_LABELS else status + "⁉️"
            )
            if new_state not in validators_change_state:
                validators_change_state[new_state] = []

            # Append the validator the list of validator that changed to th
            validators_change_state[new_state].append(index)

        # Notify all the changes of state
        for new_state, validators_index in validators_change_state.items():
            validators_str = ", ".join([str(index) for index in validators_index])
            validators_markdown = ", ".join(
                [
                    "[" + str(index) + "](" + validators.get_validator_url(index) + ")"
                    for index in validators_index
                ]
            )
            message_base = (
                f"{len(validators_index)} Validators changed to {new_state}: "
            )

            log.info(message_base + validators_str)
            await messages.send_message(message_base + validators_markdown)
