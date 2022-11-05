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

        self.validators_waiting_to_notify = {}

    async def check(self):
        log.debug("Check State of Validators")

        # Get current state of validators
        validators_state = validators.get_validators_state(
            validators=self.monitored_validators,
            batch_request_delay=self.batch_request_delay,
        )

        # Detect validators changing state
        validators_change_state = self.__get_validators_change_state(validators_state)

        # Update the notification waiting list
        max_waiting_to_notify = self.__register_validator_waiting_time_notify(
            validators_change_state,
        )

        # Decide if we should notify
        notify, reset_delay_counter = self.__should_notify_change_state(
            max_waiting_to_notify
        )

        # Reset the notification delay counter
        if reset_delay_counter or notify:
            self.validators_waiting_to_notify = {}

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

    def __register_validator_waiting_time_notify(self, validators_change_state):
        #   Get validators that changed their state
        validator_change_state_indexes = [
            item for sublist in validators_change_state.values() for item in sublist
        ]
        #   Get validators that are waiting to do some notification
        validators_waiting_to_notify_indexes = self.validators_waiting_to_notify.keys()
        #   Get validators that were waiting to notify but went back to normal
        validators_went_back_to_normal_indexes = set(
            validators_waiting_to_notify_indexes
        ) - set(validator_change_state_indexes)

        # Remove validators that went back to normal from waiting list
        validators_str = ", ".join(
            [str(index) for index in validators_went_back_to_normal_indexes]
        )
        log.info(
            f"💖 Some validators recovered. No need to notify anymore: {validators_str}"
        )
        for index in validators_went_back_to_normal_indexes:
            del self.validators_waiting_to_notify[index]

        if not validator_change_state_indexes:
            # No waiting for any notification
            max_waiting_to_notify = None
        else:
            # Waiting to do some notifications
            now = datetime.datetime.now()
            max_waiting_to_notify = now
            # Update the waiting time for validators that were not waiting before
            for index in validator_change_state_indexes:
                # Register time (if not registered already)
                waiting_to_notify = self.validators_waiting_to_notify.get(index, now)
                self.validators_waiting_to_notify[index] = waiting_to_notify

                # Calculate the validator waiting for longer
                if max_waiting_to_notify > waiting_to_notify:
                    max_waiting_to_notify = waiting_to_notify

        return max_waiting_to_notify

    def __should_notify_change_state(self, max_waiting_to_notify):
        # Decide if we should notify right away, or wait a few seconds
        notify = False
        reset_delay_counter = False

        if max_waiting_to_notify:
            # We are waiting to notify some status changes
            waiting_time = datetime.datetime.now() - max_waiting_to_notify
            remaining_time = self.notify_delay_seconds - waiting_time.total_seconds()
            if remaining_time >= 0:
                # We haven't waited enough, wait more!
                log.info(
                    f"⏱ Waiting {remaining_time:.0f}s more before notifying validator changes. Waited for {waiting_time.total_seconds():.0f}s to notify some validators changes"
                )
            else:
                # We waited enough! Notify and reset the delay
                log.info(f"✉️ Waited enough! The validator changes will be notified")
                notify = True
                reset_delay_counter = True
        else:
            # Reset the delay counters if theres no changes
            reset_delay_counter = True

        return notify, reset_delay_counter

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
