# Pico W Modbus TCP ↔ RTU Bridge

A Modbus TCP to Modbus RTU bridge running on the **Raspberry Pi Pico W** with **MicroPython**.

This device replaces a Docker-based `mbusd` container on a Pi Zero W by providing
a dedicated, low-cost hardware bridge between Modbus TCP (WiFi) and Modbus RTU (RS-485).

## Architecture

```
┌──────────────┐    Modbus TCP     ┌──────────────────┐    Modbus RTU    ┌──────────────┐
│ Modbus TCP   │ ◄──────────────► │ Pico W Bridge    │ ◄──────────────► │ Modbus RTU   │
│ Client       │    Port 502      │ (WiFi + UART)    │    RS-485 Bus    │ Slave Device │
└──────────────┘                  └──────────────────┘                  └──────────────┘
```

## Features

- **Modbus TCP → RTU conversion**: Transparently forwards TCP requests to RTU slaves via RS-485
- **WiFi connectivity**: Connects to existing WiFi network
- **CRC16 verification**: Validates all RTU frames
- **Low cost**: ~€10 in components (Pico W + MAX485)
- **Low power**: ~100 mA typical

## Directory Structure

```
├── .devcontainer/          # DevContainer configuration (VSCode + Docker)
│   ├── Dockerfile          # Container image definition
│   └── devcontainer.json   # VSCode DevContainer settings
├── .vscode/                # VSCode configuration
│   ├── tasks.json          # Build/deploy/test tasks
│   └── settings.json       # Editor settings
├── src/                    # MicroPython source code
│   ├── boot.py             # Bootstrap (runs on Pico boot)
│   ├── main.py             # Main application entry point
│   └── modbus_bridge.py    # Modbus bridge core logic
├── tests/                  # Unit tests (runs under CPython)
│   ├── __init__.py
│   ├── test_crc.py         # CRC16 calculation tests
│   ├── test_tcp_rtu.py     # TCP ↔ RTU conversion tests
│   └── test_rtu_master.py  # RTU request/response tests
├── scripts/                # Development and deployment scripts
│   ├── flash.sh            # Flash .uf2 firmware to Pico
│   ├── deploy.sh           # Deploy Python files via mpremote
│   └── test_integration.py # Integration test with pymodbus
├── docs/
│   └── wiring.md           # Hardware wiring guide
├── README.md
└── .gitignore
```

## Getting Started

### Prerequisites

- **VSCode** with **DevContainer extension**
- **Docker** installed on the host
- **Raspberry Pi Pico W**
- **RS-485 transceiver** (e.g., MAX485)
- USB cable for Pico connection

### Development Setup

1. **Clone this repository**
2. **Open in VSCode** — you'll be prompted to reopen in DevContainer
3. **Build the container** — the Dockerfile installs all tools automatically:
   - `mpremote` for deploying code to the Pico
   - `pymodbus` for Modbus testing
   - `mbpoll` for Modbus command-line testing
   - `screen` for serial monitoring
   - `pytest` for running unit tests

### Wiring

See [docs/wiring.md](docs/wiring.md) for complete wiring instructions.

### Flashing MicroPython

1. Download the latest MicroPython `.uf2` for Pico W from:
   [micropython.org/download/RPI_PICO_W](https://micropython.org/download/RPI_PICO_W/)
2. Put the Pico in BOOTSEL mode (hold BOOTSEL, connect USB)
3. Copy the `.uf2` file to the RPI-RP2 mass storage device
4. Or use the VSCode task: **Tasks: Run Task → Flash Pico**

### Deploying Code

Use the VSCode task: **Tasks: Run Task → Deploy Code**

Or manually:
```bash
mpremote connect /dev/ttyACM0 fs cp src/boot.py :boot.py
mpremote connect /dev/ttyACM0 fs cp src/main.py :main.py
mpremote connect /dev/ttyACM0 fs cp src/modbus_bridge.py :modbus_bridge.py
mpremote connect /dev/ttyACM0 reset
```

### Serial Monitor

Use the VSCode task: **Tasks: Run Task → Serial Monitor**

Or manually:
```bash
screen /dev/ttyACM0 115200
```

Exit `screen` with `Ctrl+A` then `k`, confirm with `y`.

## Testing

### Unit Tests

Run unit tests with the VSCode task or:
```bash
python -m pytest tests/ -v
```

### CRC Reference Values

The CRC unit tests use these known-good reference values:

| Frame (hex) | Expected CRC |
|-------------|-------------|
| `01 03 00 00 00 01` | `0x840A` |
| `01 03 00 00 00 03` | `0x05CB` |
| `01 05 00 00 FF 00` | `0x8CDA` |
| `01 06 00 00 00 0A` | `0x08CD` |

### Integration Test

With the Pico W running and on the network:
```bash
python scripts/test_integration.py --ip 192.168.1.100
```

Or with `mbpoll`:
```bash
mbpoll -m tcp -a 1 -r 1 -c 8 -t 4 192.168.1.100 -P 502
```

## Configuration

Edit `src/modbus_bridge.py` or create a config dict:

```python
from modbus_bridge import ModbusBridge

bridge = ModbusBridge({
    "wifi_ssid": "MyNetwork",
    "wifi_password": "secret123",
    "tcp_port": 502,
    "uart_baudrate": 19200,
    "slave_id": 1,
})
```

## Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| `device not found` | Pico not connected / wrong port | Check `ls /dev/ttyACM*` |
| `connection refused` | WiFi not connected | Check serial output for IP |
| `no response from slave` | Wrong slave ID / wiring | Verify `slave_id` and RS-485 wiring |
| `crc error` | Corrupted data / baud mismatch | Check baud rate and termination |

## License

MIT
