import os
import logging
from pathlib import Path
import yaml

CONFIG_FILE = "config.yml"
DEFAULT_LOG_LEVEL = os.environ.get("LOGLEVEL", "INFO")
BATCH_SIZE = 50

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


def getConfig():
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)
        return config
    else:
        raise Exception(f'The config file "{CONFIG_FILE}" is required')


def getLog(name, level=DEFAULT_LOG_LEVEL):
    return logging.getLogger(name)


def divide_list_in_batches(data, batch_size=BATCH_SIZE):
    for i in range(0, len(data), batch_size):
        yield data[i : i + batch_size]

def format_decimal(value, decimals=10):
    return f"{value:.{decimals}f}".rstrip('0').rstrip('.')

def escape_special_symbols(input_string, special_symbols):
    for symbol in special_symbols:
        input_string = input_string.replace(symbol, "\\" + symbol)
    return input_string


config = getConfig()
