import datetime
import validators
import messages
import prometheus
import utils

log = utils.getLog(__name__)

ONLINE_STATUS = "active_online"
STATUS_LABELS = {"active_online": "*ONLINE* 👍", "active_offline": "*OFFLINE* 🔥"}


class MonitorStatus:
    """
    Monitors a set of validators
    """

    def __init__(
        self,
        monitored_validators,
        batch_request_delay,
        notify_delay_seconds,
    ):
        self.monitored_validators = monitored_validators
        self.validators_online = {}

        self.batch_request_delay = batch_request_delay
        self.notify_delay_seconds = notify_delay_seconds

        self.notify_delay_start_time_status = None

    async def check(self):
        log.debug("Check State of Validators")

        # Get current state of validators
        validators_state = validators.get_validators_state(
            validators=self.monitored_validators,
            batch_request_delay=self.batch_request_delay,
        )

        # Detect validators changing state
        validators_change_state = self.__get_validators_change_state(validators_state)

        # Decide if we should notify
        (
            notify,
            start_delay_count,
            reset_delay_counter,
        ) = self.__should_notify_change_state(validators_change_state)

        # Update the notification delay counter
        if start_delay_count:
            self.notify_delay_start_time_status = datetime.datetime.now()
        elif reset_delay_counter:
            self.notify_delay_start_time_status = None

        # Update state, and notify all the changes of state
        await self.__update_validator_state_and_notify(validators_change_state, notify)

    def __get_validators_change_state(self, validators_state):
        validators_change_state = {}
        for validator_state in validators_state:
            index = validator_state["index"]
            status = validator_state["status"]
            is_online = status == ONLINE_STATUS
            prometheus.validator_up_gauge.labels(index=index).set(is_online)

            # Check if there are status changes
            previous_status = self.validators_online.get(index, ONLINE_STATUS)
            if status == previous_status:
                # No change in the status from last check
                continue

            if status not in validators_change_state:
                validators_change_state[status] = []

            # Append the validator the list of validator that changed
            validators_change_state[status].append(index)

        return validators_change_state

    def __should_notify_change_state(self, validators_change_state):
        # Decide if we should notify right away, or wait a few seconds
        notify = False
        start_delay_count = False
        reset_delay_counter = False

        if len(validators_change_state):
            # Some validators changed the state
            if self.notify_delay_start_time_status is None:
                # There's no prior notification being delayed. We wait before notifying
                log.info(
                    f"Detected some validator state change. Waiting {self.notify_delay_seconds}s before notifying them"
                )
                start_delay_count = True
            else:
                waiting_time = (
                    datetime.datetime.now() - self.notify_delay_start_time_status
                )
                remaining_time = (
                    self.notify_delay_seconds - waiting_time.total_seconds()
                )
                if remaining_time >= 0:
                    # We haven't waited enough, wait more!
                    log.info(
                        f"⏱ Waiting {remaining_time:.0f}s more before notifying validator changes. Waited for {waiting_time.total_seconds():.0f}s"
                    )
                else:
                    # We waited enough! Notify and reset the delay
                    log.info(
                        f"✉️ Waited enough! The validator changes will be notified"
                    )
                    notify = True
                    reset_delay_counter = True
        else:
            # Make sure there's no active waiting if there's no changes in the validator status (i.e. the validator might go back to previous state)
            if self.notify_delay_start_time_status:
                log.info(
                    f"✅ Validator State went back to NORMAL. Reseting the notification timers!"
                )
                reset_delay_counter = True

        return notify, start_delay_count, reset_delay_counter

    async def __update_validator_state_and_notify(
        self, validators_change_state, notify
    ):
        # Update state, and notify all the changes of state
        for status, validators_index in validators_change_state.items():
            if notify:
                # Change the status for the validator (only when we are also notifying)
                for index in validators_index:
                    self.validators_online[index] = status

            # Notify validator changes
            status_label = (
                STATUS_LABELS[status] if status in STATUS_LABELS else status + "??"
            )
            message_base = (
                f"{len(validators_index)} Validators changed to {status_label}: "
            )
            await messages.send_message_validators(
                message_base, validators_index, notify
            )
