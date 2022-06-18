from pathlib import Path
import yaml

CONFIG_FILE = "config.yml"

if Path(CONFIG_FILE).exists():
    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)
else:
    raise Exception(f'The config file "{CONFIG_FILE}" is required')
