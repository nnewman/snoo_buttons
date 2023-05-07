"""
Module for simple manipulations of the Snoo
"""
import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncContextManager, Callable, Coroutine, Tuple

from pubnub.pnconfiguration import PNConfiguration, PNReconnectionPolicy
from pysnoo import ActivityState, SessionLevel, Snoo, SnooAuthSession, SnooPubNub

from .constants import (
    Commands,
    CREDENTIALS_FILE,
    FORCE_LOCK,
    HOLD_ON_START,
    LOCK_LED,
    MAX_SESSION_LEVEL,
    TOKEN_FILE,
    TOKEN_UPDATE_MUTEX,
    TWENTY_MINUTES_IN_SECONDS,
)

from .utils import set_led


logger = logging.getLogger("snoo_buttons")


class CustomSnooPubNub(SnooPubNub):
    @staticmethod
    def _setup_pnconfig(access_token, uuid):
        """Generate Setup"""
        pnconfig: PNConfiguration = super(
            CustomSnooPubNub, CustomSnooPubNub
        )._setup_pnconfig(access_token, uuid)
        pnconfig.reconnect_policy = PNReconnectionPolicy.EXPONENTIAL
        return pnconfig


class NoDevicesException(Exception):
    """
    Exception when no devices are found for that Snoo instance
    """


def _get_credentials() -> Tuple[str, str]:
    with open(CREDENTIALS_FILE, "r", encoding="utf-8") as file_pointer:
        credential_data = json.load(file_pointer)
        return credential_data["username"], credential_data["password"]


def _token_updater(token):
    with open(TOKEN_FILE, "w", encoding="utf-8") as outfile:
        json.dump(token, outfile)


def _get_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "r", encoding="utf-8") as file_pointer:
        return json.load(file_pointer)


async def _get_devices_retry(snoo: Snoo, retry_count: int = 3):
    current_count = 0
    devices = None
    while current_count < retry_count:
        try:
            devices = await snoo.get_devices()
        finally:
            current_count += 1
    return devices


async def get_history(pubnub: CustomSnooPubNub) -> ActivityState:
    """
    Shows the most recent history object

    Args:
        pubnub (CustomSnooPubNub): Instance of CustomSnooPubNub

    Returns:
        ActivityState: Last activity state
    """
    history = await pubnub.history()
    return history[0] if history else None


MAP_LEVEL_TO_INT = {
    SessionLevel.BASELINE: 0,
    SessionLevel.LEVEL1: 1,
    SessionLevel.LEVEL2: 2,
    SessionLevel.LEVEL3: 3,
    SessionLevel.LEVEL4: 4,
}
MAP_INT_TO_LEVEL = {val: key for key, val in MAP_LEVEL_TO_INT.items()}


def _authorized(token: dict) -> bool:
    try:
        return (
            token
            and token.get('expires_at') 
            and datetime.fromtimestamp(token['expires_at']) > datetime.now()
        )
    except:  # noqa
        return False


@asynccontextmanager
async def get_pubnub() -> AsyncContextManager[CustomSnooPubNub]:
    """
    Gets an authenticated pubnub and yields it along with the last activity state

    Raises:
        NoDevicesException: When no devices are found

    Yields:
        Iterator[AsyncContextManager[Tuple[CustomSnooPubNub, ActivityState]]]: Tuple of
            authenticated pubnub and last activity
    """
    token = _get_token()
    force_auth = False
    async with SnooAuthSession(token, _token_updater) as auth:
        if not _authorized(token):
            os.remove(TOKEN_FILE)
            force_auth = True

        if force_auth or not auth.authorized:
            # Init Auth
            async with TOKEN_UPDATE_MUTEX:
                new_token = await auth.fetch_token(*_get_credentials())
                _token_updater(new_token)

        # Snoo API Interface
        snoo = Snoo(auth)
        devices = await _get_devices_retry(snoo)
        if not devices:
            # No devices
            raise NoDevicesException("There is no Snoo connected to that account!")

        baby = await snoo.get_baby()
        if baby.settings.weaning:
            # assuming weaning doesn't go off once buttons are turned on
            MAP_LEVEL_TO_INT[SessionLevel.WEANING_BASELINE] = 0
            MAP_LEVEL_TO_INT.pop(SessionLevel.BASELINE, None)
            MAP_INT_TO_LEVEL[0] = SessionLevel.WEANING_BASELINE

        # Snoo PubNub Interface
        pubnub = CustomSnooPubNub(
            auth.access_token,
            devices[0].serial_number,
            f"pn-pysnoo-{devices[0].serial_number}",
        )

        try:
            yield pubnub
        finally:
            await pubnub.stop()


def get_lock_status(last_activity_state: ActivityState) -> bool:
    """
    Parses the last activity for lock status

    Args:
        last_activity_state (ActivityState): Last actitity state

    Returns:
        bool: Lock status
    """
    return last_activity_state.state_machine.hold


queue = asyncio.Queue(maxsize=10)


async def toggle(pubnub: CustomSnooPubNub, last_activity_state: ActivityState):
    if last_activity_state.state_machine.state == SessionLevel.ONLINE:
        await pubnub.publish_start()
        logger.info("Started")
        if HOLD_ON_START:
            await pubnub.publish_goto_state(SessionLevel.BASELINE, True)
            logger.info("Level lock toggled")
        set_led(LOCK_LED, HOLD_ON_START)
    else:
        await pubnub.publish_goto_state(SessionLevel.ONLINE)
        set_led(LOCK_LED, False)  # Can't be locked if off!
        logger.info("Stopped")


async def up_level(pubnub: CustomSnooPubNub, last_activity_state: ActivityState):
    up_transition = last_activity_state.state_machine.up_transition
    if not up_transition.is_active_level():
        logger.warning("Tried to increase level. No valid up-transition available!")
        return
    await pubnub.publish_goto_state(up_transition)
    logger.info("Level decreased")
    set_led(LOCK_LED, get_lock_status(last_activity_state))


async def down_level(pubnub: CustomSnooPubNub, last_activity_state: ActivityState):
    down_transition = last_activity_state.state_machine.down_transition
    if not down_transition.is_active_level():
        logger.warning("Tried to decrease level. No valid down-transition available!")
    await pubnub.publish_goto_state(down_transition)
    logger.info("Level decreased")
    set_led(LOCK_LED, get_lock_status(last_activity_state))


async def lock(pubnub: CustomSnooPubNub, last_activity_state: ActivityState):
    current_state = last_activity_state.state_machine.state
    current_hold = get_lock_status(last_activity_state)
    new_hold = not current_hold
    if not current_state.is_active_level():
        logger.warning("Cannot toggle hold when Snoo is not running!")
    await pubnub.publish_goto_state(current_state, new_hold)
    logger.info("Level lock toggled")
    set_led(LOCK_LED, new_hold)


async def _set_max_level_and_lock(pubnub: CustomSnooPubNub, _):
    await pubnub.publish_goto_state(MAP_INT_TO_LEVEL[MAX_SESSION_LEVEL], FORCE_LOCK)


async def _set_lock(pubnub: CustomSnooPubNub, last_activity_state: ActivityState):
    current_state = last_activity_state.state_machine.state
    await pubnub.publish_goto_state(current_state, True)


def listener_set_level_back_to_max(last_activity_state: ActivityState):
    logger.info("Responding to activity (level callback)")

    current_level = last_activity_state.state_machine.state

    if (
        MAX_SESSION_LEVEL is not None
        and current_level.is_active_level()
        and MAP_LEVEL_TO_INT[current_level] > MAX_SESSION_LEVEL
    ):
        logger.info("Activity callback (level) must return to max")
        queue.put_nowait(Commands.SET_TO_MAX)


def listener_set_lock_if_not_on(last_activity_state: ActivityState):
    logger.info("Responding to activity (lock callback)")
    current_state = last_activity_state.state_machine.state
    if current_state.is_active_level() and not get_lock_status(last_activity_state):
        logger.info("Activity callback (lock) must set lock")
        queue.put_nowait(Commands.SET_LOCK)


def listener_update_lock_led(last_activity_state: ActivityState):
    if last_activity_state.state_machine.hold:
        set_led(LOCK_LED, True)


def dispatch(command: Commands) -> Callable:
    match command:
        case Commands.LOCK:
            return lock
        case Commands.DOWN_LEVEL:
            return down_level
        case Commands.UP_LEVEL:
            return up_level
        case Commands.TOGGLE:
            return toggle
        case Commands.SET_TO_MAX:
            return _set_max_level_and_lock
        case Commands.SET_LOCK:
            return _set_lock


def push_queue_command_callable(command: Commands) -> Callable:
    return lambda: queue.put_nowait(command)


async def worker():
    """
    Background worker to keep pubnub connection open and listen for changes or commands
    """
    while True:
        async with get_pubnub() as pubnub:
            logger.info("Watcher: Booting up!")

            pubnub: CustomSnooPubNub = pubnub  # temp! hack for typing
            pubnub.subscribe()

            unsubscribe_callbacks = [pubnub.add_listener(listener_update_lock_led)]
            if FORCE_LOCK:
                unsubscribe_callbacks.append(
                    pubnub.add_listener(listener_set_lock_if_not_on)
                )
            if MAX_SESSION_LEVEL is not None:  # it can be 0
                unsubscribe_callbacks.append(
                    pubnub.add_listener(listener_set_level_back_to_max)
                )

            logger.info("Watcher: Connected subscribers")
            logger.info("Watcher: Awaiting work")
            start_time = time.time()
            while time.time() < (start_time + TWENTY_MINUTES_IN_SECONDS):
                if queue.qsize():
                    command = queue.get_nowait()
                    logger.info(f"Watcher: command {command} received")

                    last_activity_status: ActivityState = await get_history(pubnub)
                    if not last_activity_status:
                        logger.info(
                            "No last activity status, assuming error. Recycling"
                        )
                        queue.put_nowait(command)
                        break

                    func: Coroutine[CustomSnooPubNub, ActivityState] = dispatch(command)
                    try:
                        await func(pubnub, last_activity_status)
                    except:  # noqa
                        logger.exception("Error with recent command")
                        queue.put_nowait(command)
                        break

                await asyncio.sleep(0.25)

            logger.info("Watcher: Time is up! Disconnecting subscribers.")

            for _unsubscribe_callback in unsubscribe_callbacks:
                _unsubscribe_callback()

            logger.info("Watcher: subscribers disconnected")
            pubnub.unsubscribe()
            logger.info("Watcher: Recycling!")
