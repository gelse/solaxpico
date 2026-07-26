"""
modbus_bridge.py — MicroPython Modbus TCP ↔ RTU Bridge (CPython-compatible for testing)

This module implements a Modbus TCP to Modbus RTU bridge for the
Raspberry Pi Pico W. It listens for Modbus TCP requests over WiFi
and forwards them as Modbus RTU frames over the UART interface
to connected RS-485 devices.

Hardware:
    - Raspberry Pi Pico W
    - RS-485 transceiver (e.g., MAX485) on UART1 (GP4=TX, GP5=RX)
    - DE/RE pin on GPIO6 for direction control

Dependencies:
    - umodbus (MicroPython Modbus library)
    - network (WiFi stack)
    - machine (UART, Pin)
"""

import struct

# Platform-specific imports: machine and uasyncio are MicroPython-only.
# Under CPython we provide stubs so the module can be imported for unit tests.
try:
    from machine import UART, Pin
except ImportError:
    class _StubUART:
        pass
    class _StubPin:
        pass
    UART = _StubUART
    Pin = _StubPin

try:
    import uasyncio
except ImportError:
    import asyncio as uasyncio


# Default configuration
DEFAULT_CONFIG = {
    "wifi_ssid": "ModbusBridge",
    "wifi_password": "changeme123!",
    "tcp_port": 502,
    "uart_id": 1,
    "uart_tx_pin": 4,
    "uart_rx_pin": 5,
    "uart_de_pin": 6,
    "uart_baudrate": 9600,
    "uart_data_bits": 8,
    "uart_stop_bits": 1,
    "uart_parity": None,
    "slave_id": 1,
}


class ModbusBridge:
    """Modbus TCP to RTU bridge.

    Listens for Modbus TCP requests and forwards them over UART
    as Modbus RTU frames to connected slave devices.
    """

    def __init__(self, config=None):
        """Initialize bridge with optional config overrides.

        Args:
            config: Dictionary of config keys to override DEFAULT_CONFIG.
        """
        self.config = dict(DEFAULT_CONFIG)
        if config:
            self.config.update(config)

        self._uart = None
        self._de_pin = None
        self._server = None

    def setup_uart(self):
        """Initialize the UART interface for RS-485 communication."""
        self._de_pin = Pin(self.config["uart_de_pin"], Pin.OUT, value=0)
        self._uart = UART(
            self.config["uart_id"],
            baudrate=self.config["uart_baudrate"],
            bits=self.config["uart_data_bits"],
            parity=self.config["uart_parity"],
            stop=self.config["uart_stop_bits"],
            tx=Pin(self.config["uart_tx_pin"]),
            rx=Pin(self.config["uart_rx_pin"]),
        )

    def set_de(self, value: bool):
        """Set RS-485 driver enable pin.

        Args:
            value: True = transmit, False = receive.
        """
        if self._de_pin:
            self._de_pin.value(1 if value else 0)

    def send_rtu(self, data: bytes) -> None:
        """Send Modbus RTU frame over UART.

        Args:
            data: Raw Modbus RTU bytes to transmit.
        """
        self.set_de(True)
        self._uart.write(data)
        self._uart.flush()
        self.set_de(False)

    def receive_rtu(self, timeout_ms: int = 1000) -> bytes | None:
        """Receive Modbus RTU frame over UART.

        Args:
            timeout_ms: Maximum time to wait for response in ms.

        Returns:
            Response bytes, or None if timeout.
        """
        # Simple read with timeout
        start = uasyncio.get_event_loop().time()
        buffer = bytearray()
        while (uasyncio.get_event_loop().time() - start) < (timeout_ms / 1000):
            if self._uart.any():
                chunk = self._uart.read(self._uart.any())
                if chunk:
                    buffer.extend(chunk)
            uasyncio.sleep_ms(10)
        return bytes(buffer) if buffer else None

    async def handle_client(self, reader, writer):
        """Handle an incoming Modbus TCP connection.

        Args:
            reader: Stream reader for the TCP connection.
            writer: Stream writer for the TCP connection.
        """
        try:
            data = await reader.read(256)
            if not data:
                return

            # Remove MBAP header (7 bytes) to get RTU frame
            # MBAP: transaction_id(2) + protocol_id(2) + length(2) + unit_id(1)
            transaction_id = data[0:2]
            unit_id = data[6]
            pdu = data[7:]

            # Build Modbus RTU frame: address + PDU + CRC
            rtu_frame = bytes([unit_id]) + pdu
            rtu_frame += self._calculate_crc(rtu_frame)

            # Forward over UART
            self.send_rtu(rtu_frame)
            response = self.receive_rtu()

            if response:
                # Check CRC
                if not self._verify_crc(response):
                    return

                # Strip address and CRC, wrap in MBAP header
                response_pdu = response[1:-2]
                length = struct.pack(">H", len(response_pdu) + 1)
                mbap = transaction_id + b"\x00\x00" + length + bytes([unit_id])
                writer.write(mbap + response_pdu)
                await writer.drain()
        except Exception as e:
            print("Error handling client:", e)
        finally:
            try:
                await writer.wait_closed()
            except Exception:
                pass

    @staticmethod
    def _calculate_crc(data: bytes) -> bytes:
        """Calculate Modbus CRC16 for given data.

        Args:
            data: Input bytes.

        Returns:
            Two-byte CRC16 in little-endian order.
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return struct.pack("<H", crc)

    @staticmethod
    def _verify_crc(data: bytes) -> bool:
        """Verify Modbus CRC16 for received frame.

        Args:
            data: Frame including CRC at end.

        Returns:
            True if CRC is valid.
        """
        if len(data) < 2:
            return False
        received_crc = struct.unpack("<H", data[-2:])[0]
        calculated = ModbusBridge._calculate_crc(data[:-2])
        return struct.unpack("<H", calculated)[0] == received_crc


def start():
    """Convenience entry point to start the bridge."""
    bridge = ModbusBridge()
    bridge.setup_uart()
    print("Modbus bridge initialized. Ready.")
    return bridge
