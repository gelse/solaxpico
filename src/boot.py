"""Minimal boot script for the Pico W Modbus gateway."""

import time
from machine import Pin

try:
    led = Pin("LED", Pin.OUT)
    led.on()
    time.sleep_ms(100)
    led.off()
except Exception:
    # Do not block boot/REPL if LED control is unavailable.
    pass
