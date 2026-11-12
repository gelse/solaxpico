"""
modbus_bridge.py — MicroPython-compatible Modbus library.

Provides:
  - CRC16 with 256-entry lookup table
  - TCP ↔ RTU frame conversion (MBAP ↔ RTU + CRC)
  - RTUMaster class for UART-based RTU transactions

Constraints:
  - No asyncio
  - No struct for CRC
  - MicroPython 1.20+ compatible (uses int.from_bytes / int.to_bytes)
"""

# ---------------------------------------------------------------------------
# Compatibility: CPython has a builtin TimeoutError, MicroPython does not.
# On CPython the alias IS the builtin, so tests asserting TimeoutError keep
# working; on MicroPython we fall back to a local exception class.
# ---------------------------------------------------------------------------

try:
    RTUTimeoutError = TimeoutError
except NameError:

    class RTUTimeoutError(Exception):
        pass


# ---------------------------------------------------------------------------
# CRC16 — 256-entry lookup table (Modbus polynomial 0xA001, reflected)
# ---------------------------------------------------------------------------

def _build_crc_table() -> list:
    """Precompute CRC16 lookup table for polynomial 0xA001."""
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
        table.append(crc)
    return table


_CRC_TABLE = _build_crc_table()


def modbus_crc(data: bytes) -> int:
    """
    Calculate Modbus CRC16 for *data* (excluding the CRC itself).

    Returns integer CRC value. Wire format is little-endian:
      bytes[0] = crc & 0xFF
      bytes[1] = (crc >> 8) & 0xFF

    Example:
      >>> hex(modbus_crc(b'\\x01\\x03\\x00\\x00\\x00\\x08'))
      '0xc44'
    """
    crc = 0xFFFF
    for byte in data:
        idx = (crc ^ byte) & 0xFF
        crc = (crc >> 8) ^ _CRC_TABLE[idx]
    return crc


def verify_crc(frame: bytes) -> bool:
    """
    Verify trailing CRC16 of a Modbus RTU frame.

    Returns True if the last 2 bytes match the CRC of the preceding data.
    Returns False for frames shorter than 2 bytes.
    """
    if len(frame) < 2:
        return False
    expected_crc = int.from_bytes(frame[-2:], 'little')
    return modbus_crc(frame[:-2]) == expected_crc


# ---------------------------------------------------------------------------
# TCP ↔ RTU conversion
# ---------------------------------------------------------------------------

def tcp_to_rtu(tcp_frame: bytes) -> tuple:
    """
    Convert a Modbus TCP frame to an RTU frame.

    Args:
        tcp_frame: Full Modbus TCP frame (MBAP header + unit ID + PDU).

    Returns:
        (transaction_id: bytes[2], rtu_frame: bytes)
        rtu_frame includes unit ID, PDU, and appended CRC.

    Raises:
        ValueError: If frame is too short, ProtocolID != 0, or length
                    field is inconsistent.
    """
    if len(tcp_frame) < 8:  # 7 MBAP + at least 1 PDU byte
        raise ValueError(
            f"TCP frame too short: {len(tcp_frame)} bytes, minimum 8"
        )

    tid = tcp_frame[0:2]
    pid = tcp_frame[2:4]

    if pid != b'\x00\x00':
        raise ValueError(
            f"ProtocolID != 0: got {int.from_bytes(pid, 'big')}"
        )

    length = int.from_bytes(tcp_frame[4:6], 'big')
    uid = tcp_frame[6:7]
    pdu = tcp_frame[7:]

    if length != 1 + len(pdu):
        raise ValueError(
            f"MBAP length mismatch: field says {length}, "
            f"expected {1 + len(pdu)}"
        )

    rtu_payload = uid + pdu
    crc_bytes = modbus_crc(rtu_payload).to_bytes(2, 'little')

    return (tid, rtu_payload + crc_bytes)


def rtu_to_tcp(transaction_id: bytes, rtu_frame: bytes) -> bytes:
    """
    Convert a Modbus RTU frame to a TCP frame.

    Strips and verifies the trailing CRC, then prepends a MBAP header.

    Args:
        transaction_id: 2-byte transaction ID to place in MBAP header.
        rtu_frame:      Complete RTU frame (unit ID + PDU + CRC).

    Returns:
        Complete Modbus TCP frame (MBAP + unit ID + PDU).

    Raises:
        ValueError: If frame is too short, CRC verification fails.
    """
    if len(rtu_frame) < 4:  # 1 addr + 1 PDU min + 2 CRC
        raise ValueError(
            f"RTU frame too short: {len(rtu_frame)} bytes, minimum 4"
        )

    if not verify_crc(rtu_frame):
        raise ValueError("CRC error")

    addr = rtu_frame[0:1]
    pdu = rtu_frame[1:-2]  # strip CRC
    length = 1 + len(pdu)  # unit ID + PDU

    mbap = (
        transaction_id +
        b'\x00\x00' +
        length.to_bytes(2, 'big') +
        addr +
        pdu
    )

    return mbap


# ---------------------------------------------------------------------------
# RTU Master class
# ---------------------------------------------------------------------------

try:
    import time as _time_module
except ImportError:
    _time_module = None  # Graceful fallback if run in strange env


class RTUMaster:
    """
    Modbus RTU master that sends requests and receives responses via UART.

    Timing:
      - **500 ms global timeout** from first byte sent to last byte received.
      - **5 ms inter-character silence** triggers frame-end detection once
        at least one byte has been received (≈3.5 chars at 19200 baud).

    Args:
        uart:        A MicroPython ``machine.UART`` instance (or compatible
                     mock for testing).
        baudrate:    Baud rate (default 19200). Used only for informational
                     purposes; the UART object must already be configured.
        timeout_ms:  Global transaction timeout in milliseconds (default 500).
    """

    def __init__(self, uart, baudrate=19200, timeout_ms=500):
        self.uart = uart
        self.baudrate = baudrate
        self.timeout_ms = timeout_ms
        self.interchar_ms = 5  # ≈3.5 chars @ 19200

    def transaction(self, rtu_request: bytes) -> bytes:
        """
        Send an RTU request and return the RTU response.

        1. Flush any stale data from the UART receive buffer.
        2. Write *rtu_request* to the UART.
        3. Read response bytes until:
           - Global timeout (500 ms) reached — raises ``RTUTimeoutError``
             (= builtin ``TimeoutError`` on CPython) if no bytes received;
             otherwise returns partial data.
           - Inter-character silence (5 ms) detected after at least one byte.

        Args:
            rtu_request: Complete RTU frame including CRC.

        Returns:
            Response bytes (RTU frame with CRC).

        Raises:
            RTUTimeoutError: If no byte received within *timeout_ms*.
        """
        _time = _time_module

        # 1. Flush Rx buffer
        while self.uart.any():
            self.uart.read()

        # 2. Send request
        self.uart.write(rtu_request)

        # 3. Receive response
        response = bytearray()
        start = _time.ticks_ms()
        last_byte_time = start

        while True:
            elapsed = _time.ticks_diff(_time.ticks_ms(), start)
            if elapsed > self.timeout_ms:
                if len(response) == 0:
                    raise RTUTimeoutError(
                        "No response from Modbus slave "
                        f"(timeout={self.timeout_ms}ms)"
                    )
                # Partial data — timed out waiting for more
                break

            if self.uart.any():
                response.append(self.uart.read(1)[0])
                last_byte_time = _time.ticks_ms()
            elif len(response) > 0:
                # No new byte — check inter-character silence
                silence = _time.ticks_diff(
                    _time.ticks_ms(), last_byte_time
                )
                if silence >= self.interchar_ms:
                    break  # Frame complete

        return bytes(response)
