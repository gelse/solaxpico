"""main.py — Solax Pico W Modbus TCP ↔ RTU bridge service.

Connects to Wi-Fi, then serves Modbus TCP on port 502 and translates
requests to Modbus RTU over UART0 (GP0/GP1, 19200 8N1) to the Solax
inverter, translating responses back.

Extends the Prompt-1.2 Wi-Fi stub: keeps connect_wifi()/log() and the
reconnect structure, adds the TCP server, client handling, FATAL
recovery and the watchdog.
"""

import gc
import select
import socket
import time

import machine
import network
from machine import Pin, UART

from modbus_bridge import RTUMaster, RTUTimeoutError, rtu_to_tcp, tcp_to_rtu

try:
    import wifi_config
except ImportError:
    wifi_config = None

LED = Pin("LED", Pin.OUT)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TCP_PORT = 502
MAX_CLIENTS = 4
SELECT_TIMEOUT_S = 1          # loop cadence: heartbeat + watchdog feeding
CLIENT_RECV_SIZE = 260        # max Modbus TCP ADU size
MAX_MBAP_LENGTH = 254         # unit ID + max PDU (253)
WIFI_CONNECT_TIMEOUT_S = 15
WIFI_RETRY_DELAY_S = 5
WIFI_MAX_RETRIES = 3          # consecutive Wi-Fi failures before FATAL
BRIDGE_MAX_CRASHES = 3        # consecutive unexpected failures before FATAL
RTU_TIMEOUTS_FATAL = 5        # consecutive Modbus timeouts before FATAL
UART_BAUDRATE = 19200
HEARTBEAT_INTERVAL_MS = 60000
ENABLE_WATCHDOG = True
WDT_TIMEOUT_MS = 8000

# Client service results
CLIENT_ALIVE = 0
CLIENT_CLOSED = 1
CLIENT_FATAL = 2


def log(msg):
    print("[main]", msg)


def led_blink(times, on_ms=200, off_ms=200):
    for _ in range(times):
        LED.on()
        time.sleep_ms(on_ms)
        LED.off()
        time.sleep_ms(off_ms)


def fatal(reason):
    log("FATAL: {}".format(reason))
    led_blink(3)
    machine.reset()


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------
def init_watchdog():
    if not ENABLE_WATCHDOG:
        return None
    try:
        from machine import WDT

        return WDT(timeout=WDT_TIMEOUT_MS)
    except Exception as exc:
        log("watchdog unavailable: {}".format(exc))
        return None


def feed(wdt):
    if wdt is not None:
        wdt.feed()


# ---------------------------------------------------------------------------
# Wi-Fi (kept from the deployed stub)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Modbus RTU side
# ---------------------------------------------------------------------------
def init_rtu():
    # GP0/GP1 are UART0 pins on the RP2040 (UART1 lives on GP4/GP5 etc.) —
    # the adapter is wired to GP0 (TX) / GP1 (RX), so we use UART(0).
    # This does not clash with the REPL, which runs over USB CDC.
    uart = UART(
        0,
        baudrate=UART_BAUDRATE,
        tx=Pin(0),
        rx=Pin(1),
        bits=8,
        parity=None,
        stop=1,
    )
    return RTUMaster(uart, baudrate=UART_BAUDRATE)


# ---------------------------------------------------------------------------
# Modbus TCP server
# ---------------------------------------------------------------------------
def open_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("", TCP_PORT))
    server.listen(MAX_CLIENTS)
    server.settimeout(SELECT_TIMEOUT_S)  # 1 s accept timeout
    return server


def accept_client(server, clients):
    try:
        sock, addr = server.accept()
    except OSError as exc:
        log("accept failed: {}".format(exc))
        return
    if len(clients) >= MAX_CLIENTS:
        log("client limit reached, refusing {}".format(addr))
        sock.close()
        return
    clients.append([sock, b""])
    log("client connected: {} ({}/{} clients)".format(addr, len(clients), MAX_CLIENTS))


def close_client(clients, index, reason):
    log("client disconnected ({}): {}".format(clients[index][0], reason))
    clients[index][0].close()
    del clients[index]


def service_client(conn, rtu):
    """Read available bytes from one client, answer complete Modbus TCP frames.

    conn is a [sock, rx_buffer] pair. Returns:
      CLIENT_ALIVE  — keep the connection
      CLIENT_CLOSED — protocol or socket error, drop the connection
      CLIENT_FATAL  — Modbus slave unreachable too often
    """
    sock, _ = conn
    try:
        data = sock.recv(CLIENT_RECV_SIZE)
    except OSError as exc:
        log("client recv error: {}".format(exc))
        return CLIENT_CLOSED
    if not data:
        return CLIENT_CLOSED  # client closed the connection

    conn[1] += data

    while True:
        buf = conn[1]
        if len(buf) < 7:  # 6 bytes MBAP header + at least 1 frame byte
            break
        length = int.from_bytes(buf[4:6], "big")
        if length < 2 or length > MAX_MBAP_LENGTH:
            log("invalid MBAP length {}, dropping client".format(length))
            return CLIENT_CLOSED
        need = 6 + length
        if len(buf) < need:
            break  # frame still incomplete, wait for the next chunk

        frame = buf[:need]
        conn[1] = buf[need:]

        try:
            tid, rtu_request = tcp_to_rtu(frame)
        except ValueError as exc:
            log("malformed Modbus TCP frame: {}".format(exc))
            return CLIENT_CLOSED

        try:
            rtu_response = rtu.transaction(rtu_request)
        except RTUTimeoutError:
            # No reply is sent to the TCP client (parity with the mbusd
            # setup: the client-side request timeout handles this case).
            log("modbus timeout, no response sent")
            raise

        try:
            response = rtu_to_tcp(tid, rtu_response)
        except ValueError as exc:
            log("invalid RTU response from slave: {}".format(exc))
            continue  # drop this exchange, keep the connection

        try:
            sock.sendall(response)
        except OSError as exc:
            log("client send error: {}".format(exc))
            return CLIENT_CLOSED

    return CLIENT_ALIVE


def run_bridge(rtu, wdt):
    """Run the TCP↔RTU bridge until Wi-Fi is lost.

    Returns True when the bridge exited for a recoverable reason (Wi-Fi
    lost). FATAL conditions call fatal() and never return.
    """
    rtu_timeouts = 0
    server = open_server()
    clients = []
    last_beat = time.ticks_ms()
    log("Modbus TCP server listening on port {}".format(TCP_PORT))

    try:
        while True:
            feed(wdt)

            wlan = network.WLAN(network.STA_IF)
            if not wlan.isconnected():
                LED.off()
                log("Wi-Fi lost — restarting connection loop")
                return True

            now = time.ticks_ms()
            if time.ticks_diff(now, last_beat) >= HEARTBEAT_INTERVAL_MS:
                last_beat = now
                log(
                    "heartbeat: {} client(s), rtu_timeouts={}/{}, mem_free={}".format(
                        len(clients), rtu_timeouts, RTU_TIMEOUTS_FATAL, gc.mem_free()
                    )
                )

            try:
                readable, _, _ = select.select(
                    [server] + [conn[0] for conn in clients],
                    [],
                    [],
                    SELECT_TIMEOUT_S,
                )
            except OSError as exc:
                log("select error: {}".format(exc))
                # A stale socket can poison select(); drop all clients and retry.
                while clients:
                    close_client(clients, 0, "select error")
                continue

            for sock in readable:
                if sock is server:
                    accept_client(server, clients)
                    continue
                for i, conn in enumerate(clients):
                    if conn[0] is sock:
                        try:
                            status = service_client(conn, rtu)
                        except RTUTimeoutError:
                            rtu_timeouts += 1
                            log(
                                "modbus timeout ({}/{} consecutive)".format(
                                    rtu_timeouts, RTU_TIMEOUTS_FATAL
                                )
                            )
                            if rtu_timeouts >= RTU_TIMEOUTS_FATAL:
                                fatal(
                                    "no Modbus slave reachable after {} "
                                    "consecutive timeouts".format(rtu_timeouts)
                                )
                            status = CLIENT_ALIVE
                        else:
                            rtu_timeouts = 0
                        if status == CLIENT_CLOSED:
                            close_client(clients, i, "error or closed by peer")
                        gc.collect()
                        break

    finally:
        while clients:
            close_client(clients, 0, "bridge shutdown")
        server.close()


def main():
    wdt = init_watchdog()
    wifi_failures = 0
    bridge_crashes = 0
    while True:
        feed(wdt)
        try:
            connect_wifi()
        except Exception as exc:
            wifi_failures += 1
            log(
                "Wi-Fi connect failed ({}/{}): {}".format(
                    wifi_failures, WIFI_MAX_RETRIES, exc
                )
            )
            if wifi_failures >= WIFI_MAX_RETRIES:
                fatal("Wi-Fi not recoverable after {} attempts".format(wifi_failures))
            feed(wdt)
            time.sleep(WIFI_RETRY_DELAY_S)
            continue
        wifi_failures = 0
        bridge_crashes = 0  # fresh bridge run after (re)connect

        try:
            rtu = init_rtu()
            if run_bridge(rtu, wdt):
                continue  # recoverable: Wi-Fi lost, reconnect
        except Exception as exc:
            bridge_crashes += 1
            log(
                "bridge error ({}/{}): {}".format(
                    bridge_crashes, BRIDGE_MAX_CRASHES, exc
                )
            )
            if bridge_crashes >= BRIDGE_MAX_CRASHES:
                fatal("repeated bridge failures: {}".format(exc))
            feed(wdt)
            time.sleep(WIFI_RETRY_DELAY_S)
            continue


if __name__ == "__main__":
    main()
