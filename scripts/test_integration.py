#!/usr/bin/env python3
"""test_integration.py — live Modbus TCP integration test against the Pico W bridge.

Exercises the deployed solaxpico bridge from the outside, like a real client:
TCP connect, register reads, request repetition, and the no-response timeout
behavior for an absent slave. Run it where pymodbus is available, e.g. inside
the devcontainer image:

    docker run --rm solaxpico-devcontainer:latest python scripts/test_integration.py --host <pico-ip>

Register map note: the register addresses below come from the old mbusd setup
and the Solax X3-Hybrid G4 documentation (holding 0x0000 = status/power,
input 0x0000 = temperature/PV). They are verified against the live inverter
only insofar as the bridge forwards them; content assertions are deliberately
loose (structural, not semantic).

Exit code: 0 when all tests pass, 1 otherwise.
"""

import argparse
import sys
import time

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException

SLAVE_ID = 1          # Solax inverter
GHOST_SLAVE_ID = 247  # deliberately absent → must yield a timeout, not a reset
PORT = 502
TIMEOUT_S = 5
HOLDING_START, HOLDING_COUNT = 0x0000, 32  # status, power, voltage
INPUT_START, INPUT_COUNT = 0x0000, 16      # temperature, PV voltage

results = []


def record(name, ok, detail=""):
    status = "[PASS]" if ok else "[FAIL]"
    line = f"{status} {name}" + (f" — {detail}" if detail else "")
    print(line)
    results.append(ok)


def expect_exception(fn, *args, **kwargs):
    """Run fn, return the exception raised, or None if it succeeded.

    Catches pymodbus exceptions *and* raw OSError/ConnectionResetError — the
    latter can escape pymodbus when the peer drops the TCP connection, and
    must surface as a clean [FAIL], not a traceback.
    """
    try:
        fn(*args, **kwargs)
        return None
    except (ModbusException, OSError) as exc:
        return exc


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", required=True, help="IP address of the Pico W")
    parser.add_argument("--port", type=int, default=PORT, help="Modbus TCP port")
    parser.add_argument(
        "--timeout", type=float, default=TIMEOUT_S, help="client timeout in seconds"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="pymodbus client retries (0: one failed read = one RTU timeout)",
    )
    args = parser.parse_args()

    client = ModbusTcpClient(
        args.host, port=args.port, timeout=args.timeout, retries=args.retries
    )

    # 1. TCP connect to the bridge.
    try:
        ok = client.connect()
        record("TCP connect", ok, f"{args.host}:{args.port}")
    except ConnectionException as exc:
        record("TCP connect", False, str(exc))
        print("Cannot reach the bridge — aborting.")
        return 1
    if not results[-1]:
        return 1

    # 2. Read Holding Registers (FC 03), status/power/voltage block.
    rr = expect_exception(
        client.read_holding_registers, HOLDING_START, count=HOLDING_COUNT, device_id=SLAVE_ID
    )
    if rr is None:
        record(
            "Read holding registers",
            len(rr.registers) == HOLDING_COUNT,
            f"{len(rr.registers)}/{HOLDING_COUNT} registers: {rr.registers[:8]}...",
        )
    else:
        record("Read holding registers", False, f"{type(rr).__name__}: {rr}")

    # 3. Read Input Registers (FC 04), temperature/PV block.
    ri = expect_exception(
        client.read_input_registers, INPUT_START, count=INPUT_COUNT, device_id=SLAVE_ID
    )
    if ri is None:
        record(
            "Read input registers",
            len(ri.registers) == INPUT_COUNT,
            f"{len(ri.registers)}/{INPUT_COUNT} registers: {ri.registers[:8]}...",
        )
    else:
        record("Read input registers", False, f"{type(ri).__name__}: {ri}")

    # 4. Ten requests in a row — checks framing recovery, no drift, no stuck
    #    buffers (each response must arrive individually).
    n_ok = 0
    t0 = time.monotonic()
    err = ""
    for i in range(10):
        r = expect_exception(
            client.read_holding_registers, HOLDING_START, count=8, device_id=SLAVE_ID
        )
        if r is None:
            n_ok += 1
        else:
            err = f"request {i + 1}: {type(r).__name__}: {r}"
            break
    record(
        "10 sequential requests",
        n_ok == 10,
        f"{n_ok}/10 ok in {time.monotonic() - t0:.1f} s" + (f"; {err}" if err else ""),
    )

    # 5. Ghost slave 247 — the bridge must answer with *silence* (Modbus
    #    timeout), not a connection error or a bogus exception response.
    rg = expect_exception(
        client.read_holding_registers, HOLDING_START, count=8, device_id=GHOST_SLAVE_ID
    )
    if rg is None:
        record(
            f"Slave {GHOST_SLAVE_ID} times out",
            False,
            "unexpectedly got a response — a slave with ID 247 may exist?",
        )
    elif isinstance(rg, ConnectionException):
        record(
            f"Slave {GHOST_SLAVE_ID} times out",
            False,
            f"connection dropped instead of timing out: {rg}",
        )
    else:
        record(
            f"Slave {GHOST_SLAVE_ID} times out",
            True,
            f"silent timeout as expected ({type(rg).__name__})",
        )

    client.close()

    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
