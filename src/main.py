import logging
import asyncio
import signal
from threading import Event
import traceback

import validators
import messages
import config

STATUS_LABELS = {"active_online": "*ONLINE* 👍", "active_offline": "*OFFLINE* 🔥"}

# State
validator_active = {}
error_count = 0

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)
exit = Event()
wait = None

# Config
polling_wait = config.config["check_health"]["polling_wait"]
error_count_notify_thresholds = config.config["check_health"][
    "error_count_notify_thresholds"
]
error_count_max_notify_threshold = error_count_notify_thresholds[-1]


async def updateState(monitored_validators):
    log.info("Check and Update the state for Validators")

    for validator_state in validators.get_validators_state(monitored_validators):
        index = validator_state["index"]
        status = validator_state["status"]
        previous_status = validator_active.get(index, True)

        if (status == "active_online") == previous_status:
            # No change in the status from last check
            continue

        # Change the status for the validator
        validator_active[index] = not previous_status

        # Notify the change
        state_label = (
            STATUS_LABELS[status] if status in STATUS_LABELS else status + "⁉️"
        )
        message = f"Validator *{index}* changed to {state_label}"
        await messages.send_message(message)


async def main():
    global wait, error_count

    user = await messages.get_user()
    log.info('[%s] ETH2 Monitor "%s" is up', user.username, user.first_name)
    await messages.send_message(f"☀️ Validator Monitor *RESTARTED*")

    # Get all the monitoring validators
    monitored_validators = validators.get_validators()

    log.info(
        "Monitoring %s validators: %s", len(monitored_validators), monitored_validators
    )
    await messages.send_message(
        f"Will keep an 👀 on `{len(monitored_validators)}` validators"
    )

    while not exit.is_set():
        try:
            await updateState(monitored_validators)
            error_count = 0
        except Exception as e:
            # Log errors, and notify if the errors have been happening for some consecutive runs
            error_count += 1
            log.error(traceback.format_exc())
            log.error(
                f"Error checking the state of validators (error_count={error_count}). Retrying in {polling_wait}s!"
            )

            if (
                error_count in error_count_notify_thresholds
                or error_count % error_count_max_notify_threshold == 0
            ):
                try:
                    await messages.send_message(
                        f"🔥 *ERROR*: The check has been failing for `{error_count}` times in a row! Cause: {repr(e)}"
                    )
                except Exception as e2:
                    log.error(traceback.format_exc())
                    log.error("Nested error. Error sending the Error message")
        finally:
            log.debug(f"Next check in {polling_wait} seconds")
            exit.wait(polling_wait)


async def say_goodbye():
    log.info("Have a good day Ser!")
    await messages.send_message(
        f"💤 Validator Monitor *SHUTDOWN*\. Have a nice day Ser\!"
    )


def stop(signal_number=None, _stack=None):
    log.info("Shutting down (Signal=%s)", signal_number)
    exit.set()


if __name__ == "__main__":
    for sig in ("TERM", "HUP", "INT"):
        signal.signal(getattr(signal, "SIG" + sig), stop)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # pragma: no branch
        pass
    finally:
        asyncio.run(say_goodbye())
