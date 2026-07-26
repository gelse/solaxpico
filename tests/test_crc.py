"""Tests for Modbus CRC16 calculation and verification."""

import struct
import sys
import os

# Ensure src is in path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Note: These tests validate the CRC logic by running it under CPython.
# The same ModbusBridge._calculate_crc is pure Python and runs identically
# on MicroPython.
from src.modbus_bridge import ModbusBridge


class TestCRC:
    """Test cases for Modbus CRC16.

    Reference values generated with:
    https://www.modbustools.com/modbus_crc16.html
    """

    # Known-good CRC values for common Modbus frames
    # Format: (frame_bytes, expected_crc_hex)
    REFERENCE_VALUES = [
        # Read Holding Registers (device 1, start 0, count 1)
        (b"\x01\x03\x00\x00\x00\x01", 0x840A),
        # Read Holding Registers (device 1, start 0, count 3)
        (b"\x01\x03\x00\x00\x00\x03", 0x05CB),
        # Write Single Coil (device 1, coil 0, ON)
        (b"\x01\x05\x00\x00\xFF\x00", 0x8CDA),
        # Write Single Register (device 1, reg 0, value 10)
        (b"\x01\x06\x00\x00\x00\x0A", 0x08CD),
        # Response: Read Holding Registers (3 data bytes)
        (b"\x01\x03\x06\x00\x00\x00\x01\x00\x02", 0x8479),
    ]

    def test_calculate_crc_reference_values(self):
        """CRC16 should match known-good reference values."""
        for frame, expected_crc in self.REFERENCE_VALUES:
            result_bytes = ModbusBridge._calculate_crc(frame)
            result_crc = struct.unpack("<H", result_bytes)[0]
            assert result_crc == expected_crc, (
                f"CRC mismatch for {frame.hex()}: "
                f"got 0x{result_crc:04X}, expected 0x{expected_crc:04X}"
            )

    def test_crc_is_two_bytes(self):
        """CRC should always be exactly 2 bytes (little-endian)."""
        crc = ModbusBridge._calculate_crc(b"\x01\x03\x00\x00\x00\x01")
        assert len(crc) == 2

    def test_empty_input_crc(self):
        """CRC of empty data should be 0xFFFF."""
        crc = struct.unpack("<H", ModbusBridge._calculate_crc(b""))[0]
        assert crc == 0xFFFF, f"Expected 0xFFFF, got 0x{crc:04X}"

    def test_single_byte_input(self):
        """CRC of single byte should be deterministic."""
        crc = ModbusBridge._calculate_crc(b"\x00")
        assert len(crc) == 2

    def test_verify_crc_valid(self):
        """Verify CRC should return True for valid frames."""
        for frame, _ in self.REFERENCE_VALUES:
            # Append CRC to make a complete frame
            crc = ModbusBridge._calculate_crc(frame)
            complete_frame = frame + crc
            assert ModbusBridge._verify_crc(complete_frame)

    def test_verify_crc_invalid(self):
        """Verify CRC should return False for corrupted frames."""
        valid = b"\x01\x03\x00\x00\x00\x01" + ModbusBridge._calculate_crc(
            b"\x01\x03\x00\x00\x00\x01"
        )
        # Corrupt the data
        invalid = bytearray(valid)
        invalid[2] ^= 0xFF  # Flip some bits
        assert not ModbusBridge._verify_crc(bytes(invalid))

    def test_verify_crc_too_short(self):
        """Verify CRC should return False for frames < 2 bytes."""
        assert not ModbusBridge._verify_crc(b"")
        assert not ModbusBridge._verify_crc(b"\x01")

    def test_crc_deterministic(self):
        """CRC should be deterministic for identical inputs."""
        data = b"\x01\x03\x00\x00\x00\x01"
        result1 = ModbusBridge._calculate_crc(data)
        result2 = ModbusBridge._calculate_crc(data)
        assert result1 == result2
