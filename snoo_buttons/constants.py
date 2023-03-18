"""
Constant values for the library
"""
import asyncio
import os

import gpiozero.pins.mock
from dotenv import dotenv_values
from gpiozero import Device, Button, LED


_test = os.environ.get("TEST")
ENV_FILE = ".env"
if _test:
    ENV_FILE = ".env.test"
    Device.pin_factory = gpiozero.pins.mock.MockFactory()


WORKDIR = os.path.dirname(os.path.dirname(__file__))
_config = dotenv_values(os.path.join(WORKDIR, ENV_FILE))
CREDENTIALS_FILE = os.path.join(WORKDIR, _config["CREDENTIAL_FILENAME"])
TOKEN_FILE = os.path.join(WORKDIR, _config["TOKEN_FILENAME"])
HUNDRED_KB_IN_BYTES = 1024 * 100
FIVE_MINUTES_IN_SECONDS = 300
TOKEN_UPDATE_MUTEX = asyncio.Lock()


# Pinout config
UP_BUTTON = Button(int(_config["UP_BUTTON_GPIO_PIN"]))
DOWN_BUTTON = Button(int(_config["DOWN_BUTTON_GPIO_PIN"]))
LOCK_BUTTON = Button(int(_config["LOCK_BUTTON_GPIO_PIN"]))
TOGGLE_BUTTON = Button(int(_config["TOGGLE_BUTTON_GPIO_PIN"]))
LOCK_LED = LED(int(_config["LOCK_LED_GPIO_PIN"]))
