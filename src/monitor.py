import datetime
import validators
import messages
import prometheus
import utils

log = utils.getLog(__name__)

ONLINE_STATUS = "active_online"
STATUS_LABELS = {"active_online": "*ONLINE* 👍", "active_offline": "*OFFLINE* 🔥"}
EFFECTIVENESS_LABEL_OK = "*OK* 📈"
EFFECTIVENESS_LABEL_KO = "*Critical* 🚨"


class ValidatorMonitor:
    """
    Monitors a set of validators
    """

    def __init__(
        self,
        monitored_validators,
        notify_effectiveness_threshold,
        batch_request_delay,
        notify_delay_seconds,
    ):
        self.monitored_validators = monitored_validators
        self.notify_effectiveness_threshold = notify_effectiveness_threshold
        self.validators_online = {}
        self.validators_effectiveness_ok = {}
        self.batch_request_delay = batch_request_delay
        self.notify_delay_seconds = notify_delay_seconds
        self.notify_delay_start_time = None

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
            is_online = status == ONLINE_STATUS
            prometheus.validator_up_gauge.labels(index=index).set(is_online)

            # Check if there is a statutus change
            previous_status = self.validators_online.get(index, ONLINE_STATUS)
            if status == previous_status:
                # No change in the status from last check
                continue

            if status not in validators_change_state:
                validators_change_state[status] = []

            # Append the validator the list of validator that changed to th
            validators_change_state[status].append(index)

        # Decide if we should notify right away, or wait a few seconds
        notify = False
        if len(validators_change_state):
            # Some validators changed the state
            if self.notify_delay_start_time is None:
                # There's no prior notification being delayed. We wait before notifying
                self.notify_delay_start_time = datetime.datetime.now()
                log.info(
                    f"Detected some validator state change. Waiting {self.notify_delay_seconds}s before notifying them"
                )
            else:
                waiting_time = datetime.datetime.now() - self.notify_delay_start_time
                remaining_time = (
                    self.notify_delay_seconds - waiting_time.total_seconds()
                )
                if remaining_time >= 0:
                    # We haven't waited enough, wait more!
                    log.info(
                        f"Waiting {remaining_time:.0f}s more before notifying validator changes. Waited for {waiting_time.total_seconds():.0f}s"
                    )
                else:
                    # We waited enough! Notify and reset the delay
                    log.info(f"Waited enough! The validator changes will be notified")
                    notify = True
                    self.notify_delay_start_time = None
        else:
            # Make sure there's no active waiting if there's no changes in the validator status (i.e. the validator might go back to previous state)
            self.notify_delay_start_time = None

        # Update state, and notify all the changes of state
        for status, validators_index in validators_change_state.items():
            if notify:
                for index in validators_index:
                    # Change the status for the validator (only when we are also notifying)
                    self.validators_online[index] = status
                # Reset the waiting time
                self.notify_delay_start_time = None

            # Notify validator changes
            status_label = (
                STATUS_LABELS[status] if status in STATUS_LABELS else status + "⁉️"
            )
            message_base = (
                f"{len(validators_index)} Validators changed to {status_label}: "
            )
            await self.__notify_change(message_base, validators_index, notify)

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
            prometheus.validator_effectiveness_gauge.labels(index=index).set(
                effectiveness
            )

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

    async def __notify_change(self, message_base, validators_list, notify):
        validators_str = ", ".join([str(index) for index in validators_list])
        validators_markdown = ", ".join(
            [
                "[" + str(index) + "](" + validators.get_validator_url(index) + ")"
                for index in validators_list
            ]
        )

        log.info(
            message_base + validators_str + ("" if notify else " (don't notify yet)")
        )

        if notify:
            try:
                await messages.send_message(message_base + validators_markdown)
            except:
                log.error("Error notifying change")
