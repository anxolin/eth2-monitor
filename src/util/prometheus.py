from prometheus_client import (
    start_http_server as start_server,
    Summary,
    Counter,
    Gauge,
    Info,
)
import util.utils as utils

log = utils.getLog(__name__)

PREFIX = "eth2monitor_"

config_info = Info(PREFIX + "config", "Config parameters")

validators_total_gauge = Gauge(
    PREFIX + "validators_total", "Number of validators being monitored"
)

main_loop_errors_counter = Counter(
    PREFIX + "main_loop_errors",
    "Number of errors in the main loop",
)

main_loop_consecutive_errors_gauge = Gauge(
    PREFIX + "main_loop_consecutive_errors",
    "Number of consecutive errors are currently accumulated for the last main loop executions",
)

check_time_summary = Summary(
    PREFIX + "check_seconds",
    "Time it takes to check and report the state of all the validators in every run loop",
)

bc_http_request_counter = Counter(
    PREFIX + "beaconchain_http_request",
    "Number of GET request to the Beacon Chain REST API",
)

bc_http_request_success_counter = Counter(
    PREFIX + "beaconchain_http_request_success",
    "Number of successful GET request to the Beacon Chain REST API",
)

validator_up_gauge = Gauge(
    PREFIX + "validator_up",
    "Validator efectiviness expressed in percent 0..1",
    ["index"],
)

validator_effectiveness_gauge = Gauge(
    PREFIX + "validator_effectiveness_ratio",
    "Validator efectiviness expressed in a rartio (between 0 and 1)",
    ["index"],
)


def start_http_server(port=8000):
    log.info(
        f"Start Prometheus server in port {port}. Metrics available in http://localhost:{port}"
    )
    start_server(port)


# c.inc()     # Increment by 1
# c.inc(1.6)  # Increment by given value
