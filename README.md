# ETH2 Monitor
Checks a series of validators and notifies to Telegram if they are down

> Forked from https://github.com/uijin/eth2-validator-monitor

# Docker
## Config
Rename `config-example.yaml` to `config.yaml`, modify configuration.

```bash
docker build . -t eth2-monitor
docker run -v $(pwd)/config.yaml:/app/config.yaml eth2-monitor
```

To see the logs

```bash
# get the running CONTAINER ID
docker ps

docker logs -f <CONTAINER ID>
```

# Dev
Install dependencies:
```bash
python3 -m venv ENV
source ENV/bin/activate
pip install -r requirements.txt
```

## Config
Rename `config-example.yaml` to `config.yaml`, modify configuration.

```
TELEGRAM:
  ACCESS_TOKEN: "{your bot access token}"
CHAT:
  ID: {your chat id. Reference: https://www.freecodecamp.org/news/telegram-push-notifications-58477e71b2c2/}
validator_url:
- "https://beaconcha.in/dashboard/data/validators?validators={validator_index_1,validator_index_2}
```
