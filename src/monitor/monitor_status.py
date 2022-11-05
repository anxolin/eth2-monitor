import datetime
import util.validators as validators
import util.messages as messages
import util.prometheus as prometheus
import util.utils as utils
from .monitor import Monitor

log = utils.getLog(__name__)

ONLINE_STATUS = "active_online"
STATUS_LABELS = {"active_online": "*ONLINE* 👍", "active_offline": "*OFFLINE* 🔥"}


class MonitorStatus(Monitor):
    """
    Monitors a set of validators for changes in the status
    """

    def __init__(
        self,
        monitored_validators,
        batch_request_delay,
        notify_delay_seconds,
    ):
        Monitor.__init__(
            self,
            monitored_validators=monitored_validators,
            batch_request_delay=batch_request_delay,
            notify_delay_seconds=notify_delay_seconds,
        )
        self.validators_online = {}

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
        validator_change_state_indexes = [
            item for sublist in validators_change_state.values() for item in sublist
        ]
        max_waiting_to_notify = super().update_validators_waiting_to_notify(
            validator_change_state_indexes
        )

        # Decide if we should notify
        notify, reset_delay_counter = super().should_notify_change_state(
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

    # def __register_validator_waiting_time_notify(self, validators_change_state):
    #     #   Get validators that changed their state
    #     validator_change_state_indexes = [
    #         item for sublist in validators_change_state.values() for item in sublist
    #     ]
    #     #   Get validators that are waiting to do some notification
    #     validators_waiting_to_notify_indexes = self.validators_waiting_to_notify.keys()
    #     #   Get validators that were waiting to notify but went back to normal
    #     validators_went_back_to_normal_indexes = set(
    #         validators_waiting_to_notify_indexes
    #     ) - set(validator_change_state_indexes)

    #     # Remove validators that went back to normal from waiting list
    #     validators_str = ", ".join(
    #         [str(index) for index in validators_went_back_to_normal_indexes]
    #     )
    #     log.info(
    #         f"💖 Some validators status recovered. No need to notify anymore: {validators_str}"
    #     )
    #     for index in validators_went_back_to_normal_indexes:
    #         del self.validators_waiting_to_notify[index]

    #     if not validator_change_state_indexes:
    #         # No waiting for any notification
    #         max_waiting_to_notify = None
    #     else:
    #         # Waiting to do some notifications
    #         now = datetime.datetime.now()
    #         max_waiting_to_notify = now
    #         # Update the waiting time for validators that were not waiting before
    #         for index in validator_change_state_indexes:
    #             # Register time (if not registered already)
    #             waiting_to_notify = self.validators_waiting_to_notify.get(index, now)
    #             self.validators_waiting_to_notify[index] = waiting_to_notify

    #             # Calculate the validator waiting for longer
    #             if max_waiting_to_notify > waiting_to_notify:
    #                 max_waiting_to_notify = waiting_to_notify

    #     return max_waiting_to_notify

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
