# ETH2 Monitor
Checks a series of validators and notifies to Telegram if they are down

> Forked from https://github.com/uijin/eth2-validator-monitor

# Run
## Docker-compose
Rename `config-example.yml` to `config.yml`, modify configuration.

```bash
docker-compose up
```

## Docker build
> It's simpler to just use docker-compose

```bash
docker build . -t eth2-monitor
docker run -v $(pwd)/config.yml:/app/config.yml eth2-monitor
```

To see the logs

```bash
# get the running CONTAINER ID
docker ps

docker logs -f <CONTAINER ID>
```

# Development

```bash
# Setup virtual env
python3 -m venv ENV
source ENV/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python src/main.py
```