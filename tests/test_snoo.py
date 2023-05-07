import asyncio
import os
from unittest.mock import patch

import pytest
from pysnoo import ActivityState, SessionLevel

from snoo_buttons.constants import TOKEN_FILE
from snoo_buttons.snoo import (
    get_history,
    get_pubnub,
    toggle,
    up_level,
    down_level,
    lock,
    get_lock_status,
    NoDevicesException,
)
from .fakes import (
    FakeLED,
    FakeSnoo,
    FakePubnub,
    FakeSnooAuthSession,
    generate_activity,
    generate_state_machine,
)


pytest_plugins = ('pytest_asyncio',)


def test_get_history():
    history = asyncio.run(
        get_history(FakePubnub.generate_with_history(generate_activity()))
    )
    assert history


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
async def test_get_pubnub_authorized():
    with patch(
        "snoo_buttons.snoo.CustomSnooPubNub",
        FakePubnub.generate_with_history(generate_activity()),
    ) as fake_pubnub:
        async with get_pubnub() as pubnub:
            last_activity = await get_history(pubnub)
            assert fake_pubnub.started
            assert pubnub
            assert last_activity
            assert type(last_activity) is ActivityState
        assert not fake_pubnub.started


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(False))
async def test_get_pubnub_not_authorized():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)

    with patch(
        "snoo_buttons.snoo.CustomSnooPubNub",
        FakePubnub.generate_with_history(generate_activity()),
    ) as fake_pubnub:
        async with get_pubnub() as pubnub:
            last_activity = await get_history(pubnub)
            assert fake_pubnub.started
            assert pubnub
            assert last_activity
            assert type(last_activity) is ActivityState
        assert not fake_pubnub.started

    assert os.path.exists(TOKEN_FILE)


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(False))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
async def test_get_pubnub_no_devices():
    with pytest.raises(NoDevicesException):
        async with get_pubnub() as pubnub:
            pass


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.CustomSnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.ONLINE))
    ),
)
async def test_toggle_from_online():
    async with get_pubnub() as pubnub:
        last_activity = await get_history(pubnub)
        assert last_activity.state_machine.state == SessionLevel.ONLINE
        await toggle(pubnub, last_activity)
        assert pubnub.last_message
        assert pubnub.last_message["command"] == "start_snoo"


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.CustomSnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.ONLINE))
    ),
)
@patch("snoo_buttons.snoo.HOLD_ON_START", True)
async def test_toggle_from_online_lock_on_start():
    with patch("gpiozero.LED", FakeLED) as led:
        async with get_pubnub() as pubnub:
            last_activity = await get_history(pubnub)
            assert last_activity.state_machine.state == SessionLevel.ONLINE
            await toggle(pubnub, last_activity)
            assert len(pubnub.messages) == 2
            second_last_message, last_message = pubnub.messages
            assert second_last_message["command"] == "start_snoo"
            assert last_message["hold"] == "on"

        assert led.is_on


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.CustomSnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.BASELINE))
    ),
)
async def test_toggle_from_baseline():
    async with get_pubnub() as pubnub:
        last_activity = await get_history(pubnub)
        assert last_activity.state_machine.state == SessionLevel.BASELINE
        await toggle(pubnub, last_activity)
        assert pubnub.last_message
        assert pubnub.last_message["command"] == "go_to_state"
        assert pubnub.last_message["state"] == SessionLevel.ONLINE.value


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.CustomSnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.BASELINE))
    ),
)
async def test_up_from_baseline():
    async with get_pubnub() as pubnub:
        last_activity = await get_history(pubnub)
        assert last_activity.state_machine.state == SessionLevel.BASELINE
        await up_level(pubnub, last_activity)
        assert pubnub.last_message
        assert pubnub.last_message["command"] == "go_to_state"
        assert pubnub.last_message["state"] == SessionLevel.LEVEL1.value


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.CustomSnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1))
    ),
)
async def test_up_from_level_one():
    async with get_pubnub() as pubnub:
        last_activity = await get_history(pubnub)
        assert last_activity.state_machine.state == SessionLevel.LEVEL1
        await up_level(pubnub, last_activity)
        assert pubnub.last_message
        assert pubnub.last_message["command"] == "go_to_state"
        assert pubnub.last_message["state"] == SessionLevel.LEVEL2.value


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.CustomSnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1))
    ),
)
async def test_down_from_level_one():
    async with get_pubnub() as pubnub:
        last_activity = await get_history(pubnub)
        assert last_activity.state_machine.state == SessionLevel.LEVEL1
        await down_level(pubnub, last_activity)
        assert pubnub.last_message
        assert pubnub.last_message["command"] == "go_to_state"
        assert pubnub.last_message["state"] == SessionLevel.BASELINE.value


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.CustomSnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1, True))
    ),
)
async def test_lock_from_locked():
    async with get_pubnub() as pubnub:
        last_activity = await get_history(pubnub)
        assert last_activity.state_machine.state == SessionLevel.LEVEL1
        assert last_activity.state_machine.hold == True
        await lock(pubnub, last_activity)
        assert pubnub.last_message
        assert pubnub.last_message["command"] == "go_to_state"
        assert pubnub.last_message["state"] == SessionLevel.LEVEL1.value
        assert pubnub.last_message["hold"] == "off"


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.CustomSnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1))
    ),
)
async def test_lock_from_unlocked():
    async with get_pubnub() as pubnub:
        last_activity = await get_history(pubnub)
        assert last_activity.state_machine.state == SessionLevel.LEVEL1
        assert last_activity.state_machine.hold == False
        await lock(pubnub, last_activity)
        assert pubnub.last_message
        assert pubnub.last_message["command"] == "go_to_state"
        assert pubnub.last_message["state"] == SessionLevel.LEVEL1.value
        assert pubnub.last_message["hold"] == "on"


@pytest.mark.asyncio
@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.CustomSnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1, True))
    ),
)
async def test_get_lock():
    async with get_pubnub() as pubnub:
        last_activity = await get_history(pubnub)
        assert last_activity.state_machine.state == SessionLevel.LEVEL1
        assert last_activity.state_machine.hold == True
        assert get_lock_status(last_activity)
