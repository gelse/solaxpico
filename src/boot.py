"""
boot.py — Pico W bootstrapper

This script runs automatically on Pico W boot before main.py.
It performs low-level hardware initialization and then
delegates to main.py via import.
"""

import machine
import time


def initialize():
    """Perform hardware bootstrap initialization."""
    # Set CPU frequency for power/speed balance
    machine.freq(133_000_000)  # 133 MHz (default for Pico W)

    # Give peripherals time to stabilize
    time.sleep(0.5)

    print("Pico W Modbus Bridge - Boot complete")
    print("Freq:", machine.freq() // 1_000_000, "MHz")


initialize()
