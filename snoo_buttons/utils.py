"""
Library common utility functions
"""
from gpiozero import LED


def set_led(led: LED, state: bool):
    """
    Set an LED based on given input

    Args:
        led (LED): Instance of an LED to manipulate
        state (bool): Setting for the LED
    """
    if state:
        led.on()
    else:
        led.off()


# pylint: disable=line-too-long
# From https://stackoverflow.com/questions/19425736/how-to-redirect-stdout-and-stderr-to-logger-in-python
class LoggerWriter:
    """
    Class to channel stdout and stderr to log files
    """

    def __init__(self, log_func):
        self.log_func = log_func
        self.buf = []

    def write(self, msg):
        """
        Concatenated stdout or stderr messages for Python logger

        Args:
            msg (str): Message for stdout or stderr
        """
        if msg.endswith("\n"):
            self.buf.append(msg.removesuffix("\n"))
            self.log_func("".join(self.buf))
            self.buf = []
        else:
            self.buf.append(msg)

    def flush(self):
        """
        Acts as stdout or stderr file pointer flush
        """
