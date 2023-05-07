"""
Constant values for the library
"""
import asyncio
import os
from enum import Enum
from typing import Optional

import gpiozero.pins.mock
from dotenv import dotenv_values
from gpiozero import Device, Button, LED


_test = os.environ.get("TEST")
ENV_FILE = ".env"
if _test:
    ENV_FILE = ".env.test"
    Device.pin_factory = gpiozero.pins.mock.MockFactory()


def _int_config(config: dict, key: str) -> Optional[int]:
    if key in config and isinstance(key, str) and config[key].isdigit():
        return int(config[key])


def _bool_config(config: dict, key: str, default: bool) -> bool:
    if value := config.get(key):
        return True if isinstance(value, str) and value.strip() in ('1', 'True') else False
    return default


WORKDIR = os.path.dirname(os.path.dirname(__file__))
_config = dotenv_values(os.path.join(WORKDIR, ENV_FILE))
CREDENTIALS_FILE = os.path.join(WORKDIR, _config["CREDENTIAL_FILENAME"])
TOKEN_FILE = os.path.join(WORKDIR, _config["TOKEN_FILENAME"])
HUNDRED_KB_IN_BYTES = 1024 * 100
TWENTY_MINUTES_IN_SECONDS = 1200
TOKEN_UPDATE_MUTEX = asyncio.Lock()
HOLD_ON_START = _bool_config(_config, "HOLD_ON_START", False)
MAX_SESSION_LEVEL = _int_config(_config, "MAX_SESSION_LEVEL")
FORCE_LOCK = _bool_config(_config, "FORCE_LOCK", False)


# Pinout config
UP_BUTTON = Button(int(_config["UP_BUTTON_GPIO_PIN"]))
DOWN_BUTTON = Button(int(_config["DOWN_BUTTON_GPIO_PIN"]))
LOCK_BUTTON = Button(int(_config["LOCK_BUTTON_GPIO_PIN"]))
TOGGLE_BUTTON = Button(int(_config["TOGGLE_BUTTON_GPIO_PIN"]))
LOCK_LED = LED(int(_config["LOCK_LED_GPIO_PIN"]))


class Commands(Enum):
    LOCK = "lock"
    UP_LEVEL = "up_level"
    DOWN_LEVEL = "down_level"
    TOGGLE = "toggle"
    SET_TO_MAX = "set_to_max"
    SET_LOCK = "set_lock"
