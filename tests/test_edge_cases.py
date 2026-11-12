"""Edge-case tests: empty/partial frames, max-size PDU, broadcast addressing
and Modbus exception responses."""

import pytest

from modbus_bridge import modbus_crc, rtu_to_tcp, tcp_to_rtu, verify_crc


def tcp_frame(tid: bytes, uid: int, pdu: bytes) -> bytes:
    return tid + b"\x00\x00" + (1 + len(pdu)).to_bytes(2, "big") + bytes([uid]) + pdu


def rtu_frame(uid: int, pdu: bytes) -> bytes:
    payload = bytes([uid]) + pdu
    return payload + modbus_crc(payload).to_bytes(2, "little")


class TestEmptyFrames:
    def test_tcp_to_rtu_empty(self):
        with pytest.raises(ValueError):
            tcp_to_rtu(b"")

    def test_rtu_to_tcp_empty(self):
        with pytest.raises(ValueError):
            rtu_to_tcp(b"\x00\x00", b"")

    def test_verify_crc_on_empty_frame(self):
        assert not verify_crc(b"")

    def test_crc_of_empty_payload(self):
        assert modbus_crc(b"") == 0xFFFF


class TestPartialFrames:
    def test_tcp_frame_cut_inside_mbap(self):
        full = tcp_frame(b"\x11\x22", 1, b"\x03\x00\x00\x00\x08")
        for size in range(0, 8):
            with pytest.raises(ValueError):
                tcp_to_rtu(full[:size])

    def test_rtu_frame_cut_before_crc_completes(self):
        full = rtu_frame(1, b"\x03\x00\x00\x00\x08")  # 8 bytes total
        for size in range(0, len(full)):
            with pytest.raises(ValueError):
                rtu_to_tcp(b"\x11\x22", full[:size])

    def test_verify_crc_false_for_truncated_frame(self):
        full = rtu_frame(1, b"\x03\x04")
        for size in range(len(full)):
            assert not verify_crc(full[:size])


class TestMaxSizeFrames:
    def test_256_byte_pdu_roundtrip(self):
        pdu = b"\x10" + bytes(range(255))  # 256 bytes total
        tcp = tcp_frame(b"\x7f\x7f", 0x11, pdu)

        tid, rtu = tcp_to_rtu(tcp)

        assert len(rtu) == 1 + 256 + 2
        assert verify_crc(rtu)
        assert rtu_to_tcp(tid, rtu) == tcp

    def test_large_response_frame_through_rtu_to_tcp(self):
        pdu = b"\x03\xfa" + bytes(248)  # 250-byte PDU
        rtu = rtu_frame(0x01, pdu)

        tcp = rtu_to_tcp(b"\x00\x01", rtu)

        assert tcp[4:6] == (1 + 250).to_bytes(2, "big")
        assert tcp[6:] == bytes([0x01]) + pdu


class TestBroadcastAddress:
    def test_uid_zero_write_roundtrip(self):
        tcp = tcp_frame(b"\x00\x01", 0, b"\x06\x00\x01\x00\x02")

        tid, rtu = tcp_to_rtu(tcp)

        assert rtu[0] == 0
        assert rtu_to_tcp(tid, rtu) == tcp


class TestExceptionResponses:
    @pytest.mark.parametrize(
        "function,code", [(0x83, 0x01), (0x84, 0x02), (0x90, 0x03)]
    )
    def test_exception_frame_roundtrip(self, function, code):
        tcp = tcp_frame(b"\x11\x22", 1, bytes([function, code]))

        tid, rtu = tcp_to_rtu(tcp)

        assert rtu[1] == function
        assert rtu_to_tcp(tid, rtu) == tcp

    def test_exception_rtu_frame_directly(self):
        rtu = rtu_frame(1, b"\x83\x02")  # exception code 2: illegal data address

        tcp = rtu_to_tcp(b"\x00\x05", rtu)

        assert tcp == b"\x00\x05\x00\x00\x00\x03\x01\x83\x02"


class TestTransactionIdPreservation:
    @pytest.mark.parametrize("tid", [b"\x00\x00", b"\xff\xff", b"\x12\x34"])
    def test_tid_roundtrip(self, tid):
        tcp = tcp_frame(tid, 1, b"\x03\x00\x00\x00\x02")

        rtid, rtu = tcp_to_rtu(tcp)

        assert rtid == tid
        assert rtu_to_tcp(rtid, rtu) == tcp
