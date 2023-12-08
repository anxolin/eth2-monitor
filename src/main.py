import asyncio
import signal
from threading import Event
import traceback

import util.validators as validators
import util.messages as messages
import util.utils as utils
import monitor.monitor_status as monitor_status
import monitor.monitor_effectiveness as monitor_effectiveness
import util.prometheus as prometheus
import datetime
import sys


log = utils.getLog(__name__)
exit_event = Event()
wait = None

# State
exit_code = 0
error_count = 0
last_success = None


# "check_health": {
#     "notify_error_count_thresholds": [15, 60, 1440],
#     "polling_wait": 60,
#     "batch_request_delay": 0.2,
# },
# "beacon_chain": {"base_url: https://gnosischa.in"},
# "telegram": None,
# "validators": {"eth1_withdraw_account": None, "public_keys": []},


@prometheus.check_time_summary.time()
async def check(validator_monitor, validator_effectiveness):
    # Monitor validators
    await validator_monitor.check()
    await validator_effectiveness.check()


async def main():
    global wait, error_count, last_success
    
    # Config: Health check
    check_health_config = utils.config.get("check_health", {})
    polling_wait = check_health_config.get("polling_wait", 60)
    batch_request_delay = check_health_config.get("batch_request_delay", 0.2)
    notify_delay_seconds = check_health_config.get("notify_delay_seconds", 300)
    watch_dog_kill_switch_minutes = check_health_config.get("watch_dog_kill_switch_minutes", 30)
    notify_effectiveness_threshold = check_health_config.get(
        "notify_effectiveness_threshold", None
    )
    notify_error_count_thresholds = check_health_config.get(
        "notify_error_count_thresholds", [15, 60, 1440]
    )
    error_count_max_notify_threshold = notify_error_count_thresholds[-1]

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
    validator_monitor = monitor_status.MonitorStatus(
        monitored_validators=monitored_validators,
        batch_request_delay=batch_request_delay,
        notify_delay_seconds=notify_delay_seconds,
    )
    validator_effectiveness = monitor_effectiveness.MonitorEffectiveness(
        monitored_validators=monitored_validators,
        notify_effectiveness_threshold=notify_effectiveness_threshold,
        batch_request_delay=batch_request_delay,
        notify_delay_seconds=notify_delay_seconds,
    )

    # Start Prometheus server
    if prometheus_config is not None:
        prometheus.config_info.info(
            {
                "beacon_chain_base_url": validators.base_url,
                "telegram_notifications_enabled": "Yes"
                if messages.bot is not None
                else "No",
            }
        )
        prometheus_port = prometheus_config.get("port", None)
        prometheus.start_http_server(prometheus_port)
    else:
        log.warning(
            "Prometheus metrics won't be exposed. To expose them, add prometheus configuration"
        )

    # Main loop
    last_success = datetime.datetime.now()
    while not exit_event.is_set():
        # Watchdog: NOTIFY and restart after 30 minutes of consecutive errors
        if last_success < datetime.datetime.now() - datetime.timedelta(minutes=watch_dog_kill_switch_minutes):
            watchdog_message = f"🐶 *WATCH DOG*\: Last success was more than {str(watch_dog_kill_switch_minutes).replace('.', '\.')} minutes ago\. Restarting\!"
            log.error(watchdog_message)
            try:
                await messages.send_message(watchdog_message)
            except Exception as e2:
                log.error(traceback.format_exc())
                log.error("Nested error. Error sending the Error message")
            exit_with_code(100)
            continue
            
        # Do another check
        try:
            await check(validator_monitor, validator_effectiveness)
            error_count = 0
            last_success = datetime.datetime.now()
        except Exception as e:
            # Log errors, and notify if the errors have been happening for some consecutive runs
            prometheus.main_loop_errors_counter.inc()
            error_count += 1
            log.error(traceback.format_exc())
            log.error(
                f"Error checking the state of validators (error_count={error_count}). Retrying in {polling_wait}s!"
            )

            # Notify if the error count is in the thresholds
            if (
                error_count in notify_error_count_thresholds
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
            prometheus.main_loop_consecutive_errors_gauge.set(error_count)
            log.debug(f"Next check in {polling_wait} seconds")
            exit_event.wait(polling_wait)


async def say_goodbye():
    log.info("Have a good day Ser!")
    await messages.send_message(
        f"💤 Validator Monitor *SHUTDOWN*\. Have a nice day Ser\!"
    )

def exit_with_code(code):
    global exit_code
    exit_code = code
    exit_event.set()


def stop(signal_number=None, _stack=None):
    log.info("Shutting down (Signal=%s)", signal_number)
    exit_event.set()


if __name__ == "__main__":
    for sig in ("TERM", "HUP", "INT"):
        signal.signal(getattr(signal, "SIG" + sig), stop)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # pragma: no branch
        pass
    finally:
        asyncio.run(say_goodbye())
    if exit_code != 0:
        sys.exit(exit_code)
