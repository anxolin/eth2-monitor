import os
import logging
from pathlib import Path
import yaml

CONFIG_FILE = "config.yml"
DEFAULT_LOG_LEVEL = os.environ.get("LOGLEVEL", "INFO")

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


config = getConfig()
