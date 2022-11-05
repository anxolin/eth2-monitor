import datetime
import util.validators as validators
import util.messages as messages
import util.prometheus as prometheus
import util.utils as utils
from .monitor import Monitor

log = utils.getLog(__name__)

EFFECTIVENESS_LABEL_OK = "*OK* 📈"
EFFECTIVENESS_LABEL_KO = "*Critical* 🚨"


class MonitorEffectiveness(Monitor):
    """
    Monitors a set of validators
    """

    def __init__(
        self,
        monitored_validators,
        batch_request_delay,
        notify_delay_seconds,
        notify_effectiveness_threshold,
    ):
        Monitor.__init__(
            self,
            monitored_validators=monitored_validators,
            batch_request_delay=batch_request_delay,
            notify_delay_seconds=notify_delay_seconds,
        )

        self.notify_effectiveness_threshold = notify_effectiveness_threshold
        self.validators_effectiveness_ok = {}
        self.check_effectiveness_enabled = notify_effectiveness_threshold is not None

    def __get_effectiveness_changes(self, validators_effectiveness):
        validators_change_to_ok = []
        validators_change_to_ko = []
        min_effectiveness = 1

        for validator_effectiveness in validators_effectiveness:
            index = str(validator_effectiveness["index"])
            effectiveness = validator_effectiveness["effectiveness"]
            prometheus.validator_effectiveness_gauge.labels(index=index).set(
                effectiveness
            )

            if self.check_effectiveness_enabled:
                previous_effectiveness_ok = self.validators_effectiveness_ok.get(
                    index, True
                )
                effectiveness_ok = effectiveness > self.notify_effectiveness_threshold
                # log.debug(
                #     f"Validator {index} has effectiveness of {effectiveness} (effectiveness_ok={effectiveness_ok}, previous_effectiveness_ok={previous_effectiveness_ok})"
                # )

                if effectiveness_ok == previous_effectiveness_ok:
                    # No change in the effectiveness OK effectiveness
                    continue

                validators_change = (
                    validators_change_to_ok
                    if effectiveness_ok
                    else validators_change_to_ko
                )
                validators_change.append(index)

                # Keep track of the worst effectiveness
                min_effectiveness = min(min_effectiveness, effectiveness)

        return validators_change_to_ok, validators_change_to_ko, min_effectiveness

    async def check(self):
        log.debug("Check Effectiveness of Validators")

        # Check if there are effectiveness changes
        validators_effectiveness = validators.get_validators_effectiveness(
            validators=self.monitored_validators,
            batch_request_delay=self.batch_request_delay,
        )

        # Detect effectiveness changes
        (
            validators_change_to_ok,
            validators_change_to_ko,
            min_effectiveness,
        ) = self.__get_effectiveness_changes(validators_effectiveness)

        # Update the notification waiting list
        validator_change_state_indexes = (
            validators_change_to_ok + validators_change_to_ko
        )
        max_waiting_to_notify = super().update_validators_waiting_to_notify(
            validator_change_state_indexes
        )

        notify, reset_delay_counter = super().should_notify_change_state(
            max_waiting_to_notify
        )

        # Reset the notification delay counter
        if reset_delay_counter or notify:
            self.validators_waiting_to_notify = {}

        # Update state, and notify all the changes of state
        await self.__update_validator_state_and_notify(
            validators_change_to_ok, validators_change_to_ko, notify, min_effectiveness
        )

    async def __update_validator_state_and_notify(
        self,
        validators_change_to_ok,
        validators_change_to_ko,
        notify,
        min_effectiveness,
    ):
        if notify:
            # Update the effectiveness from validators (only when notifying)
            for index in validators_change_to_ok + validators_change_to_ko:
                validator = str(index)
                # Change the effectiveness status
                previous_effectiveness_status = self.validators_effectiveness_ok.get(
                    validator, True
                )
                self.validators_effectiveness_ok[
                    validator
                ] = not previous_effectiveness_status

        if validators_change_to_ok:
            message_base = f"{len(validators_change_to_ok)} Validators effectiveness changed to {EFFECTIVENESS_LABEL_OK}: "
            await messages.send_message_validators(
                message_base, validators_change_to_ok, notify
            )

        if validators_change_to_ko:
            message_base = f"{len(validators_change_to_ko)} Validators effectiveness changed to{EFFECTIVENESS_LABEL_KO} (~{min_effectiveness:.2}%): "
            await messages.send_message_validators(
                message_base, validators_change_to_ko, notify
            )

        num_validators_change_to_ko = len(validators_change_to_ko)

    # def __should_notify_change_state(
    #     self, validators_change_to_ok, validators_change_to_ko
    # ):
    #     num_validators_change_to_ok = len(validators_change_to_ok)
    #     num_validators_change_to_ko = len(validators_change_to_ko)

    #     notify = False
    #     start_delay_count = False
    #     reset_delay_counter = False
    #     if num_validators_change_to_ok + num_validators_change_to_ko > 0:
    #         # Some validators their effectivess effectiveness
    #         if self.notify_delay_start_time is None:
    #             # There's no prior notification being delayed. We wait before notifying
    #             log.info(
    #                 f"Detected some validator effectiveness change. Waiting {self.notify_delay_seconds}s before notifying them"
    #             )
    #             start_delay_count = True
    #         else:
    #             waiting_time = datetime.datetime.now() - self.notify_delay_start_time
    #             remaining_time = (
    #                 self.notify_delay_seconds - waiting_time.total_seconds()
    #             )
    #             if remaining_time >= 0:
    #                 # We haven't waited enough, wait more!
    #                 log.info(
    #                     f"⏱ Waiting {remaining_time:.0f}s more before notifying validator effectiveness. Waited for {waiting_time.total_seconds():.0f}s"
    #                 )
    #             else:
    #                 # We waited enough! Notify and reset the delay
    #                 log.info(
    #                     f"✉️ Waited enough! The validator effectiveness will be notified"
    #                 )
    #                 notify = True
    #                 reset_delay_counter = True
    #     else:
    #         # Make sure there's no active waiting if there's no changes in the validator effectiveness (i.e. the validator might go back to previous state)
    #         if self.notify_delay_start_time:
    #             log.info(
    #                 f"✅ Validator Effectiveness went back to NORMAL. Reseting the notification timers!"
    #             )
    #             reset_delay_counter = True

    #     return notify, start_delay_count, reset_delay_counter

    # def __should_notify_change_state_old(
    #     self, validators_change_to_ok, validators_change_to_ko
    # ):
    #     num_validators_change_to_ok = len(validators_change_to_ok)
    #     num_validators_change_to_ko = len(validators_change_to_ko)

    #     notify = False
    #     start_delay_count = False
    #     reset_delay_counter = False
    #     if num_validators_change_to_ok + num_validators_change_to_ko > 0:
    #         # Some validators their effectivess effectiveness
    #         if self.notify_delay_start_time is None:
    #             # There's no prior notification being delayed. We wait before notifying
    #             log.info(
    #                 f"Detected some validator effectiveness change. Waiting {self.notify_delay_seconds}s before notifying them"
    #             )
    #             start_delay_count = True
    #         else:
    #             waiting_time = datetime.datetime.now() - self.notify_delay_start_time
    #             remaining_time = (
    #                 self.notify_delay_seconds - waiting_time.total_seconds()
    #             )
    #             if remaining_time >= 0:
    #                 # We haven't waited enough, wait more!
    #                 log.info(
    #                     f"⏱ Waiting {remaining_time:.0f}s more before notifying validator effectiveness. Waited for {waiting_time.total_seconds():.0f}s"
    #                 )
    #             else:
    #                 # We waited enough! Notify and reset the delay
    #                 log.info(
    #                     f"✉️ Waited enough! The validator effectiveness will be notified"
    #                 )
    #                 notify = True
    #                 reset_delay_counter = True
    #     else:
    #         # Make sure there's no active waiting if there's no changes in the validator effectiveness (i.e. the validator might go back to previous state)
    #         if self.notify_delay_start_time:
    #             log.info(
    #                 f"✅ Validator Effectiveness went back to NORMAL. Reseting the notification timers!"
    #             )
    #             reset_delay_counter = True

    #     return notify, start_delay_count, reset_delay_counter
