# Wiring Guide — Modbus TCP ↔ RTU Bridge on Pico W

## Overview

This document describes the hardware wiring between the Raspberry Pi Pico W
and an RS-485 transceiver for Modbus RTU communication.

## Required Components

| Component | Purpose |
|-----------|---------|
| Raspberry Pi Pico W | Main controller with WiFi |
| RS-485 transceiver (e.g., MAX485, SP3485) | Converts UART to RS-485 differential signals |
| 120 Ω resistor (optional) | Termination resistor for long bus lines |
| 5 V power supply | For RS-485 transceiver (if needed) |
| Jumper wires | For connections |

## Pin Connections

### Pico W to RS-485 Transceiver (MAX485)

| Pico W Pin | GPIO | MAX485 Pin | Description |
|-----------|------|------------|-------------|
| GP4 | 4 | DI (Driver Input) | UART1 TX → RS-485 driver input |
| GP5 | 5 | RO (Receiver Output) | RS-485 receiver → UART1 RX |
| GP6 | 6 | DE (Driver Enable) | Direction control (high=transmit) |
| GP6 | 6 | RE (Receiver Enable) | Direction control (low=receive) |
| 3.3 V | - | VCC | Power (3.3 V logic — Pico is 3.3 V) |
| GND | - | GND | Common ground |

### RS-485 Bus Connections

| MAX485 Pin | Bus Connection | Description |
|-----------|---------------|-------------|
| A (non-inverting) | RS-485 A / D+ | Differential pair positive |
| B (inverting) | RS-485 B / D- | Differential pair negative |
| GND | Shared ground | Ground reference for bus |

### Termination

- Add a **120 Ω resistor** between A and B at each end of the RS-485 bus
- Only needed for long cable runs (> 10 m) or high baud rates (> 38400)

## Connection Diagram

```
Pico W                     MAX485                    RS-485 Bus
┌───────┐                 ┌───────┐                 ┌──────────┐
│ GP4   ├────────────────►│ DI    │                 │          │
│       │                 │       │                 │  A ──────├─────►
│ GP5   │◄────────────────┤ RO    │                 │          │
│       │                 │       │                 │  B ──────├─────►
│ GP6   ├────────────────►│ DE    │                 │          │
│       │                 │       │                 │  GND ────├─────►
│       │                 │  RE   │                 │          │
│ 3.3V  ├────────────────►│ VCC   │                 └──────────┘
│ GND   ├────────────────►│ GND   │
└───────┘                 └───────┘
```

## Software Configuration

The wiring above uses the default configuration in `modbus_bridge.py`:

```python
DEFAULT_CONFIG = {
    "uart_id": 1,          # UART1
    "uart_tx_pin": 4,      # GP4
    "uart_rx_pin": 5,      # GP5
    "uart_de_pin": 6,      # GP6 (combined DE/RE)
    "uart_baudrate": 9600, # 9600 baud
    # ... other settings
}
```

## Alternative Pin Assignments

If GP4/GP5/GP6 conflict with other hardware, use UART0 instead:

| Function | UART0 Pins | UART1 Pins (Default) |
|----------|-----------|---------------------|
| TX       | GP0       | GP4                |
| RX       | GP1       | GP5                |
| DE/RE    | GP2       | GP6                |

Update the config accordingly:
```python
bridge = ModbusBridge({
    "uart_id": 0,
    "uart_tx_pin": 0,
    "uart_rx_pin": 1,
    "uart_de_pin": 2,
})
```

## Verification

1. Connect Pico W via USB
2. Open serial monitor: `screen /dev/ttyACM0 115200`
3. Check boot messages:
   ```
   Pico W Modbus Bridge - Boot complete
   Freq: 133 MHz
   ```
4. Test with `mbpoll`:
   ```
   mbpoll -m tcp -a 1 -r 1 -c 8 -t 4 192.168.1.100 -P 502
   ```
