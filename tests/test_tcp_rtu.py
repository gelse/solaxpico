"""Tests for Modbus TCP → RTU frame conversion logic.

These tests validate the MBAP-to-RTU framing logic used in the bridge.
They run under CPython using the pure-Python implementation from
modbus_bridge.py (identical to MicroPython).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.modbus_bridge import ModbusBridge, DEFAULT_CONFIG


class TestTCPtoRTU:
    """Test TCP-to-RTU frame conversion."""

    def test_config_defaults(self):
        """Default config should have all required keys."""
        bridge = ModbusBridge()
        assert bridge.config["tcp_port"] == 502
        assert bridge.config["uart_baudrate"] == 9600
        assert bridge.config["slave_id"] == 1

    def test_config_override(self):
        """Config overrides should merge with defaults."""
        bridge = ModbusBridge({"tcp_port": 1502, "slave_id": 10})
        assert bridge.config["tcp_port"] == 1502
        assert bridge.config["slave_id"] == 10
        # Non-overridden values should stay at defaults
        assert bridge.config["uart_baudrate"] == 9600

    def test_calculate_crc_known_value(self):
        """CRC should match known reference."""
        # Read Holding Registers request: 01 03 00 00 00 01
        data = b"\x01\x03\x00\x00\x00\x01"
        crc = ModbusBridge._calculate_crc(data)
        # Expected CRC: 0x840A
        assert crc == b"\x0A\x84"

    def test_verify_crc_from_rtu_frame(self):
        """Verify CRC on a complete RTU frame."""
        # Read Holding Registers with correct CRC appended: 01 03 00 00 00 01 0A 84
        frame = b"\x01\x03\x00\x00\x00\x01\x0A\x84"
        assert ModbusBridge._verify_crc(frame)

    def test_invalid_crc_rejected(self):
        """Frames with wrong CRC should be rejected."""
        # Same request but with corrupted CRC
        bad_frame = b"\x01\x03\x00\x00\x00\x01\x00\x00"
        assert not ModbusBridge._verify_crc(bad_frame)
