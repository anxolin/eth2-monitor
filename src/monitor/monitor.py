import datetime
import util.validators as validators
import util.messages as messages
import util.prometheus as prometheus
import util.utils as utils

log = utils.getLog(__name__)


class Monitor:
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
        self.batch_request_delay = batch_request_delay
        self.notify_delay_seconds = notify_delay_seconds
        self.validators_waiting_to_notify = {}

    def update_validators_waiting_to_notify(self, validator_change_state_indexes):
        #   Get validators that are waiting to do some notification
        validators_waiting_to_notify_indexes = self.validators_waiting_to_notify.keys()

        #   Get validators that were waiting to notify but went back to normal
        validators_went_back_to_normal_indexes = set(
            validators_waiting_to_notify_indexes
        ) - set(validator_change_state_indexes)

        # Remove validators that went back to normal from waiting list
        if validators_went_back_to_normal_indexes:
            validators_str = ", ".join(
                [str(index) for index in validators_went_back_to_normal_indexes]
            )
            log.info(
                f"💖 {len(validators_went_back_to_normal_indexes)} validators recovered. No need to notify anymore: {validators_str}"
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

    def should_notify_change_state(self, max_waiting_to_notify):
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
