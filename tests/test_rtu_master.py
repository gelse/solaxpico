"""Unit tests for RTUMaster using a mocked UART and a controllable clock.

MicroPython's time module (ticks_ms / ticks_diff) does not exist in CPython,
so these tests replace ``modbus_bridge._time_module`` with a fake clock.
The MockUART hands the queued response to the reader right after the request
was written, like a real RTU slave would.
"""

import pytest

import modbus_bridge
from modbus_bridge import RTUMaster

REQUEST = b"\x01\x03\x00\x00\x00\x08\x44\x0c"
RESPONSE = b"\x01\x03\x10" + bytes(16) + b"\x11\x22"


class FakeClock:
    """Replacement for the MicroPython time module used by RTUMaster."""

    def __init__(self):
        self._now_ms = 0

    def ticks_ms(self):
        return self._now_ms

    def ticks_diff(self, a, b):
        return a - b

    def advance(self, ms):
        self._now_ms += ms


class MockUART:
    """Minimal machine.UART stand-in, timed by the FakeClock."""

    def __init__(self, clock, char_delay_ms=1, idle_poll_ms=1):
        self.clock = clock
        self.written = bytearray()
        self.rx_buffer = bytearray()
        self.char_delay_ms = char_delay_ms
        self.idle_poll_ms = idle_poll_ms
        self._pending_response = None

    def queue_stale(self, data):
        """Put noise into the Rx buffer before the request is sent."""
        self.rx_buffer.extend(data)

    def respond(self, data):
        """Schedule the slave's answer; becomes readable after the request."""
        self._pending_response = bytes(data)

    def any(self):
        if not self.rx_buffer:
            self.clock.advance(self.idle_poll_ms)
        return len(self.rx_buffer)

    def read(self, n=1):
        data = bytes(self.rx_buffer[:n])
        del self.rx_buffer[:n]
        self.clock.advance(self.char_delay_ms * len(data))
        return data

    def write(self, data):
        self.written.extend(data)
        if self._pending_response is not None:
            self.rx_buffer.extend(self._pending_response)
            self._pending_response = None


@pytest.fixture()
def clock():
    return FakeClock()


@pytest.fixture()
def uart(clock):
    return MockUART(clock)


@pytest.fixture()
def master(monkeypatch, clock, uart):
    monkeypatch.setattr(modbus_bridge, "_time_module", clock)
    return RTUMaster(uart, baudrate=19200, timeout_ms=500)


class TestTransaction:
    def test_returns_complete_response_after_interchar_silence(self, master, uart, clock):
        uart.respond(RESPONSE)
        result = master.transaction(REQUEST)

        assert result == RESPONSE
        assert isinstance(result, bytes)
        assert uart.written == REQUEST
        # Frame-end detection (5 ms of silence) must end the transaction long
        # before the global timeout elapses.
        assert clock.ticks_ms() < master.timeout_ms

    def test_flushes_stale_rx_bytes_before_sending(self, master, uart):
        uart.queue_stale(b"\xde\xad\xbe\xef")
        uart.respond(RESPONSE)

        result = master.transaction(REQUEST)

        assert result == RESPONSE
        assert b"\xde\xad" not in result
        assert uart.written == REQUEST

    def test_raises_timeout_error_without_response(self, master, uart):
        with pytest.raises(TimeoutError):
            master.transaction(REQUEST)
        assert uart.written == REQUEST

    def test_returns_partial_data_when_timeout_hits_mid_frame(self, monkeypatch):
        # 200 bytes arriving every 4 ms: the inter-character gaps stay below
        # the 5 ms frame-end threshold, so the global timeout cuts the frame.
        clock = FakeClock()
        uart = MockUART(clock, char_delay_ms=4)
        monkeypatch.setattr(modbus_bridge, "_time_module", clock)
        master = RTUMaster(uart, baudrate=19200, timeout_ms=500)

        uart.respond(bytes(range(200)))

        result = master.transaction(REQUEST)

        assert 0 < len(result) < 200
        assert clock.ticks_ms() > master.timeout_ms

    def test_uses_5ms_frame_end_gap_by_default(self, master):
        assert master.interchar_ms == 5
