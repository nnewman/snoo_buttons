"""
Main library executable function, meant to be run as a background process
"""
import asyncio
import logging
import logging.handlers
import os
import sys

from snoo_buttons.constants import (
    Commands,
    DOWN_BUTTON,
    HUNDRED_KB_IN_BYTES,
    LOCK_BUTTON,
    UP_BUTTON,
    TOGGLE_BUTTON,
    WORKDIR,
)
from snoo_buttons.snoo import (
    push_queue_command_callable,
    worker
)
from snoo_buttons.utils import LoggerWriter


logger = logging.getLogger("snoo_buttons")
log_path = os.path.join(WORKDIR, "logs", "snoo_buttons.log")
handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=HUNDRED_KB_IN_BYTES)
formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


sys.stdout = LoggerWriter(logger.info)
sys.stderr = LoggerWriter(logger.error)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.create_task(worker())


UP_BUTTON.when_pressed = push_queue_command_callable(Commands.UP_LEVEL)
DOWN_BUTTON.when_pressed = push_queue_command_callable(Commands.DOWN_LEVEL)
LOCK_BUTTON.when_pressed = push_queue_command_callable(Commands.LOCK)
TOGGLE_BUTTON.when_pressed = push_queue_command_callable(Commands.TOGGLE)


loop.run_forever()
