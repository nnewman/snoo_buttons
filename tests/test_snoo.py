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
    update_lock_led,
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


def test_get_history():
    history = asyncio.run(
        get_history(FakePubnub.generate_with_history(generate_activity()))
    )
    assert history


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
def test_get_pubnub_authorized():
    async def inner():
        with patch(
            "snoo_buttons.snoo.SnooPubNub",
            FakePubnub.generate_with_history(generate_activity()),
        ) as fake_pubnub:
            async with get_pubnub() as (pubnub, last_activity):
                assert fake_pubnub.started
                assert pubnub
                assert last_activity
                assert type(last_activity) is ActivityState
            assert not fake_pubnub.started

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(False))
def test_get_pubnub_not_authorized():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)

    async def inner():
        with patch(
            "snoo_buttons.snoo.SnooPubNub",
            FakePubnub.generate_with_history(generate_activity()),
        ) as fake_pubnub:
            async with get_pubnub() as (pubnub, last_activity):
                assert fake_pubnub.started
                assert pubnub
                assert last_activity
                assert type(last_activity) is ActivityState
            assert not fake_pubnub.started

    asyncio.run(inner())
    assert os.path.exists(TOKEN_FILE)


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(False))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
def test_get_pubnub_no_devices():
    async def inner():
        with pytest.raises(NoDevicesException):
            async with get_pubnub() as (pubnub, last_activity):
                pass

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.ONLINE))
    ),
)
def test_toggle_from_online():
    async def inner():
        async with get_pubnub() as (pubnub, last_activity):
            assert last_activity.state_machine.state == SessionLevel.ONLINE
            await toggle()
            assert pubnub.last_message
            assert pubnub.last_message["command"] == "start_snoo"

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.ONLINE))
    ),
)
@patch("snoo_buttons.snoo.HOLD_ON_START", True)
def test_toggle_from_online_lock_on_start():
    async def inner():
        async with get_pubnub() as (pubnub, last_activity):
            assert last_activity.state_machine.state == SessionLevel.ONLINE
            await toggle()
            assert len(pubnub.messages) == 2
            second_last_message, last_message = pubnub.messages
            assert second_last_message["command"] == "start_snoo"
            assert last_message["hold"] == "on"

    with patch("gpiozero.LED", FakeLED) as led:
        asyncio.run(inner())
        assert led.is_on


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.BASELINE))
    ),
)
def test_toggle_from_baseline():
    async def inner():
        async with get_pubnub() as (pubnub, last_activity):
            assert last_activity.state_machine.state == SessionLevel.BASELINE
            await toggle()
            assert pubnub.last_message
            assert pubnub.last_message["command"] == "go_to_state"
            assert pubnub.last_message["state"] == SessionLevel.ONLINE.value

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.BASELINE))
    ),
)
def test_up_from_baseline():
    async def inner():
        async with get_pubnub() as (pubnub, last_activity):
            assert last_activity.state_machine.state == SessionLevel.BASELINE
            await up_level()
            assert pubnub.last_message
            assert pubnub.last_message["command"] == "go_to_state"
            assert pubnub.last_message["state"] == SessionLevel.LEVEL1.value

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1))
    ),
)
def test_up_from_level_one():
    async def inner():
        async with get_pubnub() as (pubnub, last_activity):
            assert last_activity.state_machine.state == SessionLevel.LEVEL1
            await up_level()
            assert pubnub.last_message
            assert pubnub.last_message["command"] == "go_to_state"
            assert pubnub.last_message["state"] == SessionLevel.LEVEL2.value

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1))
    ),
)
def test_down_from_level_one():
    async def inner():
        async with get_pubnub() as (pubnub, last_activity):
            assert last_activity.state_machine.state == SessionLevel.LEVEL1
            await down_level()
            assert pubnub.last_message
            assert pubnub.last_message["command"] == "go_to_state"
            assert pubnub.last_message["state"] == SessionLevel.BASELINE.value

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1, True))
    ),
)
def test_lock_from_locked():
    async def inner():
        async with get_pubnub() as (pubnub, last_activity):
            assert last_activity.state_machine.state == SessionLevel.LEVEL1
            assert last_activity.state_machine.hold == True
            await lock()
            assert pubnub.last_message
            assert pubnub.last_message["command"] == "go_to_state"
            assert pubnub.last_message["state"] == SessionLevel.LEVEL1.value
            assert pubnub.last_message["hold"] == "off"

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1))
    ),
)
def test_lock_from_unlocked():
    async def inner():
        async with get_pubnub() as (pubnub, last_activity):
            assert last_activity.state_machine.state == SessionLevel.LEVEL1
            assert last_activity.state_machine.hold == False
            await lock()
            assert pubnub.last_message
            assert pubnub.last_message["command"] == "go_to_state"
            assert pubnub.last_message["state"] == SessionLevel.LEVEL1.value
            assert pubnub.last_message["hold"] == "on"

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1, True))
    ),
)
def test_get_lock():
    async def inner():
        async with get_pubnub() as (pubnub, last_activity):
            assert last_activity.state_machine.state == SessionLevel.LEVEL1
            assert last_activity.state_machine.hold == True
            assert get_lock_status(last_activity)

    asyncio.run(inner())


@patch("snoo_buttons.snoo.Snoo", FakeSnoo.generate(True))
@patch("snoo_buttons.snoo.SnooAuthSession", FakeSnooAuthSession.generate(True))
@patch(
    "snoo_buttons.snoo.SnooPubNub",
    FakePubnub.generate_with_history(
        generate_activity(generate_state_machine(SessionLevel.LEVEL1, True))
    ),
)
def test_get_lock():
    with patch("gpiozero.LED", FakeLED) as led:
        asyncio.run(update_lock_led())
        assert led.is_on
