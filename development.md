# Development

## Setup project
Fitst check out the code:
```bash
git clone https://github.com/anxolin/eth2-monitor
```

Then create a basic configuration

```bash
# Use the template to start your own configuration file
cp config-example.yml config.yml
```

## Docker-compose
The simplest way to run the project is using docker-compose.

```bash
# Start the bot
docker-compose up -d

# Check the logs
docker-compose logs -f bot

# To rebuild the image
docker-compose build
```

## Docker build
To build the image:

```bash
# Build image
docker build . -t anxolin/eth2-monitor:latest

# Run
docker run -v $(pwd)/config.yml:/app/config.yml anxolin/eth2-monitor
```

To see the logs:

```bash
# get the running CONTAINER ID
docker ps

docker logs -f <CONTAINER ID>
```

To push image:
```bash
docker push anxolin/eth2-monitor:latest
```

## Python Development

```bash
# Setup virtual env
python3 -m venv ENV
source ENV/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python src/main.py

# Change the log level
LOGLEVEL=DEBUG python src/main.py
```

## Format code
```
black src
```