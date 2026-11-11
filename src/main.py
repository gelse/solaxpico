"""Service stub: connect to Wi-Fi and idle.

This is a minimal first service for deployment/connection testing. It connects
to Wi-Fi using credentials from `wifi_config.py` and then does nothing else.
"""

import time

import network
from machine import Pin

try:
    import wifi_config
except ImportError:
    wifi_config = None


LED = Pin("LED", Pin.OUT)
WIFI_CONNECT_TIMEOUT_S = 15
WIFI_RETRY_DELAY_S = 5


def log(msg):
    print("[main]", msg)


def connect_wifi():
    if wifi_config is None:
        raise RuntimeError("wifi_config.py not found on device")

    ssid = getattr(wifi_config, "WIFI_SSID", "")
    password = getattr(wifi_config, "WIFI_PASS", "")
    if not ssid or ssid == "CHANGE_ME":
        raise RuntimeError("WIFI_SSID is missing or still set to stub value")

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        log("already connected: {}".format(wlan.ifconfig()[0]))
        LED.on()
        return wlan

    log("connecting to Wi-Fi: {}".format(ssid))
    wlan.connect(ssid, password)

    deadline = time.time() + WIFI_CONNECT_TIMEOUT_S
    while time.time() < deadline:
        if wlan.isconnected():
            LED.on()
            log("connected: {}".format(wlan.ifconfig()[0]))
            return wlan
        LED.toggle()
        time.sleep_ms(250)

    LED.off()
    raise RuntimeError("Wi-Fi connection timed out")


def main():
    while True:
        try:
            connect_wifi()
            # Service stub: connected and idle.
            while True:
                wlan = network.WLAN(network.STA_IF)
                if not wlan.isconnected():
                    LED.off()
                    log("Wi-Fi disconnected, retrying...")
                    break
                time.sleep(1)
        except Exception as exc:
            LED.off()
            log("error: {}".format(exc))
            time.sleep(WIFI_RETRY_DELAY_S)


if __name__ == "__main__":
    main()
