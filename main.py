"""
Main library executable function, meant to be run as a background process
"""
import asyncio
import logging
import logging.handlers
import os
import sys

from snoo_buttons.constants import (
    DOWN_BUTTON,
    HUNDRED_KB_IN_BYTES,
    LOCK_BUTTON,
    UP_BUTTON,
    TOGGLE_BUTTON,
    WORKDIR,
)
from snoo_buttons.snoo import down_level, lock, periodic_lock_state_updater, toggle, up_level
from snoo_buttons.utils import callback, LoggerWriter


logger = logging.getLogger("snoo_buttons")
log_path = os.path.join(WORKDIR, "logs", "snoo_buttons.log")
handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=HUNDRED_KB_IN_BYTES)
formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


sys.stdout = LoggerWriter(logger.info)
sys.stderr = LoggerWriter(logger.error)


loop = asyncio.get_event_loop()


loop.create_task(periodic_lock_state_updater())


UP_BUTTON.when_pressed = callback(loop, up_level)
DOWN_BUTTON.when_pressed = callback(loop, down_level)
LOCK_BUTTON.when_pressed = callback(loop, lock)
TOGGLE_BUTTON.when_pressed = callback(loop, toggle)

loop.run_forever()
