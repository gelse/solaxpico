"""Unit tests for TCP <-> RTU frame conversion (tcp_to_rtu, rtu_to_tcp)."""

import pytest

from modbus_bridge import modbus_crc, rtu_to_tcp, tcp_to_rtu, verify_crc

TID = b"\x11\x22"
READ_REQUEST_TCP = b"\x11\x22\x00\x00\x00\x06\x01\x03\x00\x00\x00\x08"
READ_REQUEST_RTU = b"\x01\x03\x00\x00\x00\x08\x44\x0c"


def rtu_frame(uid_pdu: bytes) -> bytes:
    """Build a valid RTU frame (unit ID + PDU + trailing CRC)."""
    return uid_pdu + modbus_crc(uid_pdu).to_bytes(2, "little")


class TestTcpToRtu:
    def test_valid_read_request(self):
        tid, rtu = tcp_to_rtu(READ_REQUEST_TCP)
        assert tid == TID
        assert rtu == READ_REQUEST_RTU

    def test_transaction_id_preserved_verbatim(self):
        tid, _ = tcp_to_rtu(b"\xff\xff\x00\x00\x00\x06\x02\x03\x00\x00\x00\x02")
        assert tid == b"\xff\xff"

    def test_nonzero_protocol_id_rejected(self):
        with pytest.raises(ValueError):
            tcp_to_rtu(b"\x11\x22\x00\x01\x00\x06\x01\x03\x00\x00\x00\x08")

    @pytest.mark.parametrize(
        "frame",
        [
            b"",                              # empty
            b"\x11\x22\x00\x00\x00",          # 5 bytes, no unit ID/PDU
            b"\x11\x22\x00\x00\x00\x06\x01",  # 7 bytes, MBAP complete, PDU missing
        ],
    )
    def test_frame_shorter_than_mbap_plus_pdu_rejected(self, frame):
        with pytest.raises(ValueError):
            tcp_to_rtu(frame)

    def test_mbap_length_mismatch_rejected(self):
        # Length field says 5 bytes follow, but unit ID + PDU are 7 bytes.
        with pytest.raises(ValueError):
            tcp_to_rtu(b"\x11\x22\x00\x00\x00\x05\x01\x03\x00\x00\x00\x08")

    def test_broadcast_uid_zero_accepted(self):
        # Broadcast write single register (function 06) to unit ID 0.
        tid, rtu = tcp_to_rtu(b"\x00\x01\x00\x00\x00\x06\x00\x06\x00\x01\x00\x02")
        assert rtu == b"\x00\x06\x00\x01\x00\x02\x58\x1a"
        assert tid == b"\x00\x01"


class TestRtuToTcp:
    def test_valid_response_frame(self):
        response = rtu_frame(b"\x01\x03\x10" + bytes(16))  # 17 data bytes + addr
        tcp = rtu_to_tcp(b"\x33\x44", response)
        assert tcp[0:2] == b"\x33\x44"
        assert tcp[2:4] == b"\x00\x00"          # protocol ID always 0
        assert tcp[4:6] == (1 + 18).to_bytes(2, "big")
        assert tcp[6:] == b"\x01\x03\x10" + bytes(16)

    def test_transaction_id_preserved(self):
        for tid in (b"\x00\x00", b"\xff\xff"):
            tcp = rtu_to_tcp(tid, READ_REQUEST_RTU)
            assert tcp[0:2] == tid

    def test_crc_error_rejected(self):
        bad = bytearray(READ_REQUEST_RTU)
        bad[-1] ^= 0xFF
        with pytest.raises(ValueError):
            rtu_to_tcp(TID, bytes(bad))

    @pytest.mark.parametrize(
        "frame",
        [
            b"",              # empty
            b"\x01\x03\x44",  # 3 bytes: shorter than addr + CRC
            b"\x01\x03\x00\x00",  # 4 bytes: structurally long enough, CRC wrong
        ],
    )
    def test_frames_shorter_than_addr_pdu_crc_rejected(self, frame):
        with pytest.raises(ValueError):
            rtu_to_tcp(TID, frame)


class TestRoundtrip:
    def test_read_request_roundtrip(self):
        tid, rtu = tcp_to_rtu(READ_REQUEST_TCP)
        assert rtu_to_tcp(tid, rtu) == READ_REQUEST_TCP

    def test_exception_response_roundtrip(self):
        # Function code 0x83 = exception response to function 0x03.
        tcp = b"\x00\x09\x00\x00\x00\x03\x01\x83\x02"
        tid, rtu = tcp_to_rtu(tcp)
        assert rtu_to_tcp(tid, rtu) == tcp

    def test_multi_register_write_roundtrip(self):
        pdu = b"\x10\x00\x00\x00\x02\x04" + b"\xaa\x55\x01\x02"
        tcp = b"\x00\x07\x00\x00" + (1 + len(pdu)).to_bytes(2, "big") + b"\x01" + pdu
        tid, rtu = tcp_to_rtu(tcp)
        assert verify_crc(rtu)
        assert rtu_to_tcp(tid, rtu) == tcp
