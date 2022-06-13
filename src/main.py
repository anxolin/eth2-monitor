import logging
import asyncio
import signal
from threading import Event
import traceback

import validators
import messages
import config

STATUS_LABELS = {
    'active_online': '*ONLINE* 👍',
    'active_offline': '*OFFLINE* 🔥'
}

# State
validator_active = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)
exit = Event()
wait = None

# Config
polling_wait = config.config['check_health']['polling_wait']


async def updateState(monitored_validators):
    log.info('Check and Update the state for Validators')

    raise Exception("fake error!")

    for validator_state in validators.get_validators_state(monitored_validators):
        index = validator_state['index']
        status = validator_state['status']
        previous_status = validator_active.get(index, True)

        if (status == 'active_online') == previous_status:
            # No change in the status from last check
            continue

        # Change the status for the validator
        validator_active[index] = not previous_status

        # Notify the change
        state_label = STATUS_LABELS[status] if status in STATUS_LABELS else status + '⁉️'
        message = f'Validator *{index}* changed to {state_label}'
        await messages.send_message(message)
        
    
async def main():
    global wait

    user = await messages.get_user()
    log.info('[%s] ETH2 Monitor "%s" is up', user.username, user.first_name)
    await messages.send_message(f"☀️ Validator Monitor *RESTARTED*")

    # Get all the monitoring validators
    monitored_validators = validators.get_validators()

    log.info('Monitoring %s validators: %s', len(monitored_validators), monitored_validators)
    await messages.send_message(f"Will keep an 👀 on `{len(monitored_validators)}` validators")


    while not exit.is_set():
        try:
            await updateState(monitored_validators)
        except Exception as e:
            log.error("Unhandled error\n", traceback.format_exc())           
        finally:
            exit.wait(polling_wait)


async def say_goodbye():    
    await messages.send_message(f"💤 Validator Monitor *SHUTDOWN*\. Have a nice day Ser\!")
    log.info("Have a good day Ser!")


def stop(signal_number=None, _stack=None):
    log.info("Shutting down (Signal=%s)", signal_number)
    exit.set()


if __name__ == '__main__':
    for sig in ('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), stop)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # pragma: no branch
        pass
    finally:
        asyncio.run(say_goodbye())