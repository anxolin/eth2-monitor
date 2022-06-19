from prometheus_client import start_http_server as start_server, Summary
import utils

# Create a metric to track time spent and requests made.
VALIDATOR_CHECK_TIME = Summary(
    "validators_check_seconds",
    "Time it takes to check and report the state of all the validators in every run loop",
)

log = utils.getLog(__name__)


def start_http_server(port=8000):
    log.info(
        f"Start Prometheus server in port {port}. Metrics available in http://localhost:{port}"
    )
    start_server(port)
