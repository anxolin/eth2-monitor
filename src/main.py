import asyncio
import signal
from threading import Event
import traceback

import validators
import messages
import utils
import monitor
import prometheus

log = utils.getLog(__name__)
exit = Event()
wait = None

# State
error_count = 0


# "check_health": {
#     "error_count_notify_thresholds": [15, 60, 1440],
#     "polling_wait": 60,
#     "batch_request_delay": 0.2,
# },
# "beacon_chain": {"base_url: https://beacon.gnosischain.com"},
# "telegram": None,
# "validators": {"eth1_withdraw_account": None, "public_keys": []},


async def main():
    global wait, error_count

    # Config: Health check
    check_health_config = utils.config.get("check_health", {})
    polling_wait = check_health_config.get("polling_wait", 60)
    batch_request_delay = check_health_config.get("batch_request_delay", 0.2)
    error_count_notify_thresholds = check_health_config.get(
        "error_count_notify_thresholds", [15, 60, 1440]
    )
    error_count_max_notify_threshold = error_count_notify_thresholds[-1]

    # Config: Prometheus
    prometheus_config = utils.config.get("prometheus", None)

    # Greet
    user = await messages.get_user()
    log.info('[%s] ETH2 Monitor "%s" is up', user.username, user.first_name)
    await messages.send_message(f"☀️ Validator Monitor *RESTARTED*")

    # Get all the monitoring validators
    monitored_validators = validators.get_validators()
    validators_total = len(monitored_validators)

    # Report the number of validators being monitored
    prometheus.validators_total_gauge.set(validators_total)
    log.info("Monitoring %s validators: %s", validators_total, monitored_validators)
    await messages.send_message(
        f"Will keep an 👀 on `{len(monitored_validators)}` validators"
    )
    validator_monitor = monitor.ValidatorMonitor(
        monitored_validators, batch_request_delay
    )

    # Start Prometheus server
    if prometheus_config is not None:
        prometheus_port = prometheus_config.get("port", None)
        prometheus.start_http_server(prometheus_port)
    else:
        log.warning(
            "Prometheus metrics won't be exposed. To expose them, add prometheus configuration"
        )

    # Main loop
    while not exit.is_set():
        try:
            # Monitor validators
            await validator_monitor.check()
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
