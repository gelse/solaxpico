#!/usr/bin/env python3
"""
test_integration.py — Integration test for the Modbus TCP ↔ RTU bridge.

This script sends Modbus TCP requests to the Pico W and verifies
responses. It requires:
  - The Pico W to be running the bridge and reachable on the network
  - pymodbus to be installed (pip install pymodbus)

Usage:
  python scripts/test_integration.py [--ip PICO_IP] [--port PORT] [--slave SLAVE_ID]

Examples:
  python scripts/test_integration.py --ip 192.168.1.100
  python scripts/test_integration.py --ip 192.168.1.100 --port 502 --slave 1
"""

import argparse
import sys
import time

try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    print("pymodbus not installed. Install with: pip install pymodbus")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Integration test for Pico W Modbus TCP ↔ RTU bridge"
    )
    parser.add_argument(
        "--ip",
        default=None,
        help="IP address of the Pico W bridge",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=502,
        help="TCP port (default: 502)",
    )
    parser.add_argument(
        "--slave",
        type=int,
        default=1,
        help="Slave/unit ID (default: 1)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # If no IP provided, prompt for it
    ip = args.ip
    if not ip:
        ip = input("Enter Pico W IP address: ").strip()
        if not ip:
            print("IP address is required.")
            sys.exit(1)

    print(f"Connecting to Pico W bridge at {ip}:{args.port} ...")
    client = ModbusTcpClient(ip, port=args.port)
    client.connect()

    if not client.is_socket_open():
        print("ERROR: Could not connect to bridge.")
        print("Make sure the Pico W is running and reachable.")
        sys.exit(1)

    print("Connected successfully!")
    print()

    # Test 1: Read Holding Registers
    print("Test 1: Read Holding Registers (slave={}, address=0, count=8)".format(args.slave))
    try:
        result = client.read_holding_registers(address=0, count=8, slave=args.slave)
        if result.isError():
            print(f"  ERROR: {result}")
        else:
            print(f"  OK: registers={result.registers}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()

    # Test 2: Read Input Registers
    print("Test 2: Read Input Registers (slave={}, address=0, count=4)".format(args.slave))
    try:
        result = client.read_input_registers(address=0, count=4, slave=args.slave)
        if result.isError():
            print(f"  ERROR: {result}")
        else:
            print(f"  OK: registers={result.registers}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()

    # Test 3: Read Coils
    print("Test 3: Read Coils (slave={}, address=0, count=8)".format(args.slave))
    try:
        result = client.read_coils(address=0, count=8, slave=args.slave)
        if result.isError():
            print(f"  ERROR: {result}")
        else:
            print(f"  OK: coils={result.bits}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()
    print("Integration test complete.")
    client.close()


if __name__ == "__main__":
    main()
