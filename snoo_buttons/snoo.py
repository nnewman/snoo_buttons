"""
Module for simple manipulations of the Snoo
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncContextManager, Tuple

from pysnoo import ActivityState, SessionLevel, Snoo, SnooAuthSession, SnooPubNub

from .constants import (
    CREDENTIALS_FILE,
    FIVE_MINUTES_IN_SECONDS,
    HOLD_ON_START,
    LOCK_LED,
    TOKEN_FILE,
    TOKEN_UPDATE_MUTEX,
)

from .utils import set_led


logger = logging.getLogger("snoo_buttons")


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


async def get_history(pubnub: SnooPubNub) -> ActivityState:
    """
    Shows the most recent history object

    Args:
        pubnub (SnooPubNub): Instance of SnooPubNub

    Returns:
        ActivityState: Last activity state
    """
    history = await pubnub.history()
    return history[0] if history else None


@asynccontextmanager
async def get_pubnub() -> AsyncContextManager[Tuple[SnooPubNub, ActivityState]]:
    """
    Gets an authenticated pubnub and yields it along with the last activity state

    Raises:
        NoDevicesException: When no devices are found

    Yields:
        Iterator[AsyncContextManager[Tuple[SnooPubNub, ActivityState]]]: Tuple of authenticated
            pubnub and last activity
    """
    async with SnooAuthSession(_get_token(), _token_updater) as auth:
        if not auth.authorized:
            # Init Auth
            async with TOKEN_UPDATE_MUTEX:
                new_token = await auth.fetch_token(_get_credentials)
                _token_updater(new_token)

        # Snoo API Interface
        snoo = Snoo(auth)
        devices = await _get_devices_retry(snoo)
        if not devices:
            # No devices
            raise NoDevicesException("There is no Snoo connected to that account!")

        # Snoo PubNub Interface
        pubnub = SnooPubNub(
            auth.access_token,
            devices[0].serial_number,
            f"pn-pysnoo-{devices[0].serial_number}",
        )

        last_activity_state = await get_history(pubnub)
        try:
            yield pubnub, last_activity_state
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


async def toggle():
    """
    Turns the Snoo on if off, and off if on
    """
    async with get_pubnub() as (pubnub, last_activity_state):
        if last_activity_state.state_machine.state == SessionLevel.ONLINE:
            await pubnub.publish_start()
            logger.info("Started")
            if HOLD_ON_START:
                await pubnub.publish_goto_state(SessionLevel.BASELINE, True)
                logger.info("Level lock toggled")
                set_led(LOCK_LED, True)
            else:
                set_led(LOCK_LED, False)  # Not locked if just turned on!
        else:
            await pubnub.publish_goto_state(SessionLevel.ONLINE)
            set_led(LOCK_LED, False)  # Can't be locked if off!
            logger.info("Stopped")


async def up_level():
    """
    Increases Snoo level setting
    """
    async with get_pubnub() as (pubnub, last_activity_state):
        up_transition = last_activity_state.state_machine.up_transition
        if up_transition.is_active_level():
            # Toggle
            await pubnub.publish_goto_state(up_transition)
            logger.info("Level decreased")
        else:
            logger.warning("Tried to increase level. No valid up-transition available!")
        set_led(LOCK_LED, get_lock_status(last_activity_state))


async def down_level():
    """
    Decreases Snoo level setting
    """
    async with get_pubnub() as (pubnub, last_activity_state):
        down_transition = last_activity_state.state_machine.down_transition
        if down_transition.is_active_level():
            # Toggle
            await pubnub.publish_goto_state(down_transition)
            logger.info("Level decreased")
        else:
            logger.warning(
                "Tried to decrease level. No valid down-transition available!"
            )
        set_led(LOCK_LED, get_lock_status(last_activity_state))


async def lock():
    """
    Toggles Snoo level lock
    """
    async with get_pubnub() as (pubnub, last_activity_state):
        current_state = last_activity_state.state_machine.state
        current_hold = get_lock_status(last_activity_state)
        new_hold = not current_hold
        if current_state.is_active_level():
            # Toggle
            await pubnub.publish_goto_state(current_state, new_hold)
            logger.info("Level lock toggled")
            set_led(LOCK_LED, new_hold)
        else:
            logger.warning("Cannot toggle hold when Snoo is not running!")


async def update_lock_led():
    """
    Sets the lock LED based on lock status
    """
    async with get_pubnub() as (_, last_activity_state):
        set_led(LOCK_LED, get_lock_status(last_activity_state))


async def periodic_lock_state_updater():
    """
    Periodically updates LED lock status every 5 minutes
    """
    while True:
        await update_lock_led()
        await asyncio.sleep(FIVE_MINUTES_IN_SECONDS)
