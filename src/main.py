"""
main.py — Modbus TCP ↔ RTU Bridge main entry point

This is the main application for the Raspberry Pi Pico W.
It initializes WiFi, sets up the Modbus bridge, and starts
the async TCP server.

Runs on MicroPython.
"""

import network
import uasyncio
import time
from src.modbus_bridge import ModbusBridge


WIFI_SSID = "ModbusBridge"
WIFI_PASSWORD = "changeme123!"
TCP_PORT = 502
LED_PIN = "LED"  # Built-in LED on Pico W


def connect_wifi():
    """Connect to WiFi access point.

    Returns:
        True if connected, False otherwise.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 30
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1

    if wlan.isconnected():
        print("WiFi connected:", wlan.ifconfig()[0])
        return True
    else:
        print("WiFi connection failed!")
        return False


async def main():
    """Application entry point."""
    # Connect to WiFi
    if not connect_wifi():
        print("Cannot start bridge without WiFi")
        return

    # Initialize bridge
    bridge = ModbusBridge()
    bridge.setup_uart()
    print("Modbus bridge ready on port", TCP_PORT)

    # Start TCP server
    server = await uasyncio.start_server(
        bridge.handle_client, "0.0.0.0", TCP_PORT
    )
    print("Server listening on 0.0.0.0:", TCP_PORT)

    try:
        # Run forever
        await server.wait_closed()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    uasyncio.run(main())
