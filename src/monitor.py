import validators
import messages
import prometheus
import utils

log = utils.getLog(__name__)

STATUS_LABELS = {"active_online": "*ONLINE* 👍", "active_offline": "*OFFLINE* 🔥"}
EFFECTIVENESS_LABEL_OK = "*OK* 📈"
EFFECTIVENESS_LABEL_KO = "*Critical* 🚨"


class ValidatorMonitor:
    """
    Monitors a set of validators
    """

    def __init__(
        self, monitored_validators, notify_effectiveness_threshold, batch_request_delay
    ):
        self.monitored_validators = monitored_validators
        self.notify_effectiveness_threshold = notify_effectiveness_threshold
        self.validators_online = {}
        self.validators_effectiveness_ok = {}
        self.batch_request_delay = batch_request_delay

    @prometheus.check_time_summary.time()
    async def check(self):
        await self.__check_state()
        await self.__check_effectiveness()

    async def __check_state(self):
        log.debug("Check State of Validators")

        validators_change_state = {}
        validators_state = validators.get_validators_state(
            validators=self.monitored_validators,
            batch_request_delay=self.batch_request_delay,
        )
        for validator_state in validators_state:
            index = validator_state["index"]
            status = validator_state["status"]
            previous_status = self.validators_online.get(index, True)

            if (status == "active_online") == previous_status:
                # No change in the status from last check
                continue

            # Change the status for the validator
            is_online = not previous_status
            self.validators_online[index] = is_online

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
            message_base = (
                f"{len(validators_index)} Validators changed to {new_state}: "
            )
            await self.__notify_change(message_base, validators_index)

    async def __check_effectiveness(self):
        log.debug("Check Effectiveness of Validators")

        validators_effectiveness = validators.get_validators_effectiveness(
            validators=self.monitored_validators,
            batch_request_delay=self.batch_request_delay,
        )

        await self.__notify_effectiveness_changes(validators_effectiveness)

    async def __notify_effectiveness_changes(self, validators_effectiveness):
        validators_change_to_ok = []
        validators_change_to_ko = []
        min_effectiveness = 1
        notify = self.notify_effectiveness_threshold is not None

        for validator_effectiveness in validators_effectiveness:
            index = str(validator_effectiveness["index"])
            effectiveness = validator_effectiveness["effectiveness"]
            prometheus.validator_effectiveness.labels(index=index).set(effectiveness)

            if notify:
                previous_effectiveness_ok = self.validators_effectiveness_ok.get(
                    index, True
                )
                effectiveness_ok = effectiveness > self.notify_effectiveness_threshold
                # log.debug(
                #     f"Validator {index} has effectiveness of {effectiveness} (effectiveness_ok={effectiveness_ok}, previous_effectiveness_ok={previous_effectiveness_ok})"
                # )

                if effectiveness_ok == previous_effectiveness_ok:
                    # No change in the effectiveness OK status
                    continue

                # Change the effectiveness status
                self.validators_effectiveness_ok[index] = effectiveness_ok
                validators_change = (
                    validators_change_to_ok
                    if effectiveness_ok
                    else validators_change_to_ko
                )
                validators_change.append(index)

                # Keep track of the worst effectiveness
                min_effectiveness = min(min_effectiveness, effectiveness)

        num_validators_change_to_ok = len(validators_change_to_ok)
        if num_validators_change_to_ok > 0:
            message_base = f"{num_validators_change_to_ok} Validators effectiveness changed to {EFFECTIVENESS_LABEL_OK}: "
            await self.__notify_change(message_base, validators_change_to_ok)

        num_validators_change_to_ko = len(validators_change_to_ko)
        if num_validators_change_to_ko > 0:
            message_base = f"{num_validators_change_to_ko} Validators effectiveness changed to {EFFECTIVENESS_LABEL_KO}: "
            await self.__notify_change(message_base, validators_change_to_ko)

        num_validators_change_to_ko = len(validators_change_to_ko)

    async def __notify_change(self, message_base, validators_list):
        validators_str = ", ".join([str(index) for index in validators_list])
        validators_markdown = ", ".join(
            [
                "[" + str(index) + "](" + validators.get_validator_url(index) + ")"
                for index in validators_list
            ]
        )

        log.info(message_base + validators_str)
        await messages.send_message(message_base + validators_markdown)
