from datetime import datetime, timedelta
from typing import Optional

from pysnoo.models import (
    ActivityState,
    Device,
    EventType,
    SessionLevel,
    Signal,
    SSID,
    StateMachine,
)


def generate_state_machine(
    state: SessionLevel = SessionLevel.ONLINE, hold: bool = False
):
    if state == SessionLevel.ONLINE:
        up_transition, down_transition = None, None
    elif state == SessionLevel.BASELINE:
        up_transition = SessionLevel.LEVEL1
        down_transition = SessionLevel.ONLINE
    elif state == SessionLevel.LEVEL1:
        up_transition = SessionLevel.LEVEL2
        down_transition = SessionLevel.BASELINE
    return StateMachine(
        up_transition=up_transition,
        since_session_start=timedelta(hours=1),
        sticky_white_noise=False,
        weaning=False,
        time_left=timedelta(hours=1),
        session_id="123",
        state=state,
        is_active_session=True,
        down_transition=down_transition,
        hold=hold,
        audio=False,
    )


def generate_activity(
    state_machine: StateMachine = None, event: EventType = EventType.ACTIVITY
):
    if not state_machine:
        state_machine = generate_state_machine()
    return ActivityState(
        left_safety_clip=True,
        rx_signal=Signal(rssi=1, strength=1),
        right_safety_clip=True,
        sw_version="123",
        event_time=datetime.now(),
        state_machine=state_machine,
        system_state="123",
        event=event,
    )


class FakeLED:
    def __init__(self, pin, initial_state: bool = False):
        self._state = initial_state

    def on(self):
        self._state = True

    def off(self):
        self._state = False

    @property
    def is_on(self):
        return self._state


class FakeButton:
    def __init__(self, pin):
        pass


class FakePubnub:
    def __init__(self, *args, **kwargs):
        self.started = True
        self._history = []
        self._messages = []

    async def history(self):
        return self._history

    async def publish(self, msg):
        self._messages.append(msg)

    async def publish_goto_state(
        self, level: SessionLevel, hold: Optional[bool] = None
    ):
        """Publish a message a go_to_state command to the Snoo control command channel"""
        msg = {"command": "go_to_state", "state": level.value}
        if hold is not None:
            msg["hold"] = "on" if hold else "off"
        return await self.publish(msg)

    async def publish_start(self):
        """Publish a message a start_snoo command to the Snoo control command channel"""
        return await self.publish({"command": "start_snoo"})

    def __call__(self, *args, **kwargs):
        return self

    async def stop(self):
        self.started = False

    @property
    def last_message(self):
        if not self._messages:
            return None
        return self._messages[-1]

    @classmethod
    def generate_with_history(cls, current_history):
        klass = cls()
        klass._history.append(current_history)
        return klass


class FakeSnoo:
    def __init__(self, *args, **kwargs):
        self.devices = []

    async def get_devices(self):
        return self.devices

    def __call__(self, *args, **kwargs):
        return self

    @classmethod
    def generate(cls, devices: bool):
        klass = cls()
        if devices:
            dt = datetime.now()
            klass.devices = [
                Device(
                    baby="John Doe",
                    created_at=dt,
                    firmware_update_date=dt,
                    firmware_version="123",
                    last_provision_success=dt,
                    last_ssid=SSID(name="network", updated_at=dt),
                    serial_number="123",
                    timezone="America/New_York",
                    updated_at=dt,
                )
            ]
        return klass


_TOKEN = {
    "token_type": "Bearer",
    "expires_in": 10800,
    "access_token": "123",
    "scope": ["offline_access"],
    "refresh_token": "123",
    "groups": ["Users"],
    "userId": "123",
    "expires_at": 1678739126.134292,
}


class FakeSnooAuthSession:
    @property
    def access_token(self):
        return _TOKEN["access_token"]

    async def fetch_token(self, callback):
        if self.authorized:
            return _TOKEN

    async def __aenter__(self):
        self.authorized = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def __call__(self, *args, **kwargs):
        return self

    @classmethod
    def generate(cls, authorized: bool = False):
        klass = cls()
        if authorized:
            klass.authorized = True
        return klass
