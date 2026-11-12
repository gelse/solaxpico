"""Unit tests for the Modbus CRC16 helpers (modbus_bridge.modbus_crc, verify_crc)."""

import pytest

from modbus_bridge import modbus_crc, verify_crc

# Reference request: slave 1, function 03, start 0x0000, count 8.
REQUEST_READ_8 = b"\x01\x03\x00\x00\x00\x08"
CRC_READ_8 = 0x0C44
CRC_READ_8_WIRE = b"\x44\x0c"


class TestModbusCrc:
    def test_known_solax_read_request(self):
        assert modbus_crc(REQUEST_READ_8) == CRC_READ_8

    def test_wire_format_is_low_byte_first(self):
        assert CRC_READ_8.to_bytes(2, "little") == CRC_READ_8_WIRE

    def test_catalogue_check_value_123456789(self):
        # CRC-16/MODBUS catalogue check value.
        assert modbus_crc(b"123456789") == 0x4B37

    def test_read_one_register_request(self):
        # 01 03 00 00 00 01 -> wire bytes 84 0A (CRC integer is 0x0A84).
        assert modbus_crc(b"\x01\x03\x00\x00\x00\x01").to_bytes(2, "little") == b"\x84\x0a"

    def test_empty_payload_keeps_init_value(self):
        assert modbus_crc(b"") == 0xFFFF

    def test_crc_depends_on_payload(self):
        assert modbus_crc(b"\x01") != modbus_crc(b"\x02")


class TestVerifyCrc:
    def test_valid_frame_accepted(self):
        assert verify_crc(REQUEST_READ_8 + CRC_READ_8_WIRE)

    def test_corrupted_payload_rejected(self):
        frame = bytearray(REQUEST_READ_8 + CRC_READ_8_WIRE)
        frame[0] ^= 0x01
        assert not verify_crc(bytes(frame))

    def test_corrupted_crc_rejected(self):
        frame = bytearray(REQUEST_READ_8 + CRC_READ_8_WIRE)
        frame[-1] ^= 0xFF
        assert not verify_crc(bytes(frame))

    @pytest.mark.parametrize("frame", [b"", b"\x01", b"\x44\x0c"])
    def test_frames_shorter_than_two_bytes_rejected(self, frame):
        assert not verify_crc(frame)

    def test_broadcast_and_exception_frames_roundtrip(self):
        payloads = (
            b"\x00\x06\x00\x01\x00\x02",  # broadcast write single register
            b"\x01\x83\x02",              # exception response (illegal data address)
        )
        for payload in payloads:
            wire = modbus_crc(payload).to_bytes(2, "little")
            assert verify_crc(payload + wire)
            assert not verify_crc(payload + bytes(reversed(wire)))

    @pytest.mark.parametrize(
        "payload",
        [
            b"\x01\x03\x00\x00\x00\x02",
            b"\x11\x04\x00\x08\x00\x02",
            bytes(range(64)),
        ],
    )
    def test_roundtrip_various_payloads(self, payload):
        frame = payload + modbus_crc(payload).to_bytes(2, "little")
        assert verify_crc(frame)
