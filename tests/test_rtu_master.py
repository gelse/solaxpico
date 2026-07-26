"""Tests for RTU master request building and response parsing.

These tests validate the protocol-level framing logic used in the
bridge. They run under CPython but test pure-Python functions that
are identical on MicroPython.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.modbus_bridge import ModbusBridge


class TestRTUMaster:
    """Test RTU request building and response parsing."""

    def test_calculate_crc_read_holding(self):
        """CRC for Read Holding Registers (addr=1, reg=0, count=1)."""
        data = b"\x01\x03\x00\x00\x00\x01"
        crc = ModbusBridge._calculate_crc(data)
        assert crc == b"\x0A\x84"

    def test_calculate_crc_read_input(self):
        """CRC for Read Input Registers (addr=1, reg=0, count=1)."""
        data = b"\x01\x04\x00\x00\x00\x01"
        crc = ModbusBridge._calculate_crc(data)
        assert crc == b"\x31\xCA"

    def test_calculate_crc_write_single_coil(self):
        """CRC for Write Single Coil (addr=1, coil=0, ON)."""
        data = b"\x01\x05\x00\x00\xFF\x00"
        crc = ModbusBridge._calculate_crc(data)
        assert crc == b"\xDA\x8C"

    def test_calculate_crc_write_single_register(self):
        """CRC for Write Single Register (addr=1, reg=0, value=10)."""
        data = b"\x01\x06\x00\x00\x00\x0A"
        crc = ModbusBridge._calculate_crc(data)
        assert crc == b"\xCD\x08"

    def test_calculate_crc_presets(self):
        """CRC for Preset Multiple Registers."""
        data = b"\x01\x10\x00\x00\x00\x02\x04\x00\x0A\x00\x0B"
        crc = ModbusBridge._calculate_crc(data)
        assert len(crc) == 2

    def test_verify_crc_on_complete_frames(self):
        """Verify CRC on complete RTU frames (data + CRC)."""
        # Read Holding Registers: 01 03 00 00 00 01 + CRC(0A84)
        frame = b"\x01\x03\x00\x00\x00\x01\x0A\x84"
        assert ModbusBridge._verify_crc(frame)

        # Write Single Coil: 01 05 00 00 FF 00 + CRC(DA_8C)
        frame = b"\x01\x05\x00\x00\xFF\x00\xDA\x8C"
        assert ModbusBridge._verify_crc(frame)

    def test_verify_crc_corrupted(self):
        """Corrupted frames should fail CRC check."""
        # Correct frame
        ok = b"\x01\x03\x00\x00\x00\x01\x0A\x84"
        assert ModbusBridge._verify_crc(ok)

        # Corrupt the address byte
        bad = bytearray(ok)
        bad[0] = 0x02
        assert not ModbusBridge._verify_crc(bytes(bad))

        # Corrupt the function code
        bad = bytearray(ok)
        bad[1] = 0x04
        assert not ModbusBridge._verify_crc(bytes(bad))
