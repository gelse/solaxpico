# Solax Pico W Modbus Gateway

A Raspberry Pi Pico W runs a Modbus TCP ↔ RTU bridge for a Solax X3-Hybrid G4
inverter. TCP clients on the LAN (port 502) talk standard Modbus TCP; the Pico
translates each request to Modbus RTU, forwards it over RS485 to the inverter,
and translates the reply back. It replaces a Raspberry Pi Zero W running
mbusd — no Linux, no SD card, no Docker on the device, just MicroPython.

**The whole build costs around 10–12 €** — Pico W ~7 €, step-down converter
~2 €, TTL-to-RS485 module ~1.2 €, plus a recycled RJ45 cable end and some
printer filament. Details in the [hardware description](doc/hardware.md#parts-cost).

Behavior matches the old mbusd setup: an unreachable inverter produces no TCP
reply (the client's request timeout applies), and the bridge keeps serving.

## Overview

| | Pi Zero W (old) | Pico W (this project) |
|---|---|---|
| Runtime | Linux + mbusd daemon | MicroPython, bare metal |
| Boot to serving | ~30 s (Linux boot + service start) | seconds (no OS) |
| Storage | SD card (corruption risk) | onboard flash |
| Bridge logic | mbusd | `src/modbus_bridge.py` + `src/main.py` |
| Supply | 17 V → step-down → 5 V | measured 14.8 V from COM pin 3 → Mini-560 → VSYS |

The Pico handles up to 4 sequential TCP clients (in practice one: the home
automation box). A hardware watchdog (8 s) and a FATAL-recovery loop restart
the device if Wi-Fi cannot be re-established or the bridge crashes repeatedly.

Modbus facts: RTU at 19200 baud 8N1, slave ID 1, TCP port 502.

## Hardware

Shopping list:

| # | Part | Notes |
|---|---|---|
| 1 | Raspberry Pi Pico W | MicroPython firmware, see Quick Start |
| 2 | Mini 560 DC-DC step-down (5 V) | input must cover the **measured** COM supply voltage — 14.8 V on this unit, manual says +13 V nominal, it varies |
| 3 | RS485-to-TTL adapter (auto-direction) | Joy-IT COM-TTL-RS485 type; no DE/RE pin needed |
| 4 | RJ45 plug + Ethernet cable | custom crimp, two pairs only, under 10 m |

Wiring (full schematics, color code, and bring-up notes in
[doc/hardware.md](doc/hardware.md)):

```
Solax COM pin 3 (+13V)  ──► Mini-560 IN+   ──► 5V ──► Pico VSYS
Solax COM pin 4 (485A)  ──► adapter A+
Solax COM pin 5 (485B)  ──► adapter B−
Solax COM pin 6 (GND)   ──► adapter E, Mini-560 IN−

Pico GP0 (UART0 TX)     ──► adapter TXD    (adapter input)
Pico GP1 (UART0 RX)     ◄── adapter RXD    (adapter output)
Pico 3V3(OUT)           ──► adapter VCC    (3.3 V logic level)
Pico GND                ──► adapter GND
```

Only the blue pair (pins 4/5 → RS485) and the green pair (pins 3/6 → power)
of the RJ45 are used. Start without 120 Ω bus termination; add one across
A+/B− only if you see framing errors or echoes.

> **Power warning:** measure the COM pin 3 voltage on your inverter before
> wiring the Mini-560 into the Pico. On this unit it is 14.8 V, not the
> manual's nominal 13 V. Verify 5.0 V (± 5 %) on the Mini-560 output before
> connecting VSYS.

**Enclosure:** the Pico, Mini-560 and RS485 adapter fit in a 3D-printed case —
see the [Enclosure section in doc/hardware.md](doc/hardware.md#enclosure) for
previews. The editable FreeCAD project is
[`case/solaxpico.FCStd`](case/solaxpico.FCStd). The case has a hole in one
side for the CAT cable; a future version will use a proper RJ45 connector with
fixed lids.

## Software architecture

```
                 Pico W (MicroPython)
 ┌───────────────────────────────────────────────┐
 │  TCP :502 ◄── main.py (select loop, ≤4 cli)   │
 │                  │ tcp_to_rtu / rtu_to_tcp    │
 │                  ▼                            │
 │            modbus_bridge.py                   │
 │            (CRC16, MBAP↔RTU, RTUMaster)       │
 │                  │ UART0 19200 8N1            │
 └──────────────────┼────────────────────────────┘
                    ▼
        RS485 adapter ◄──► Solax X3-Hybrid G4
```

- `src/main.py` — Wi-Fi connect (reconnect loop), TCP server, per-client MBAP
  framing buffer, FATAL recovery, optional watchdog (`ENABLE_WATCHDOG` in the
  source, on by default).
- `src/modbus_bridge.py` — pure library: CRC16 with 256-entry table, MBAP ↔
  RTU conversion with full validation, `RTUMaster` for UART transactions with
  5 ms inter-character frame-end detection and a 500 ms global timeout.
- `src/boot.py` — minimal bootstrap (LED blink; never blocks boot).
- `wifi_config.py` — your credentials; not in the repo (gitignored).

Recovery behavior:

| Situation | Reaction |
|---|---|
| Modbus timeout (inverter off, unwired) | no TCP reply, timeout counter in logs, connection stays open — **no reset** (mbusd parity) |
| Wi-Fi connect failure | retry 3× (5 s apart), then FATAL: LED blinks 3×, `machine.reset()` |
| Unexpected bridge crash | retry 3×, then FATAL reset |
| Hang (bug) | hardware watchdog fires after 8 s |

## Quick start

1. **Open the devcontainer** (VSCode: *Reopen in Container*), or use the
   docker-based Make targets from any machine — see Testing below.
2. **Configure Wi-Fi:** `cp wifi_config.example.py wifi_config.py`, then edit
   in your SSID/password (2.4 GHz only).
3. **Flash MicroPython:** hold BOOTSEL while plugging in the Pico, run
   `make firmware`. It downloads `RPI_PICO_W-latest.uf2` (cached in
   `firmware/`) and copies it to the RPI-RP2 drive.
4. **Wire the hardware** per [doc/hardware.md](doc/hardware.md) — and measure
   the Mini-560 output before connecting the Pico.
5. **Deploy:** `make deploy` (host with mpremote) or `make deploy_docker`
   (through the devcontainer image — no local mpremote needed). This copies
   `boot.py`, `main.py`, `modbus_bridge.py`, `wifi_config.py` and resets the
   Pico. In VSCode, the same actions are the **Flash Pico**, **Deploy Code**,
   and **Deploy & Reset** tasks.
6. **Verify:** serial monitor shows
   `Modbus TCP server listening on port 502`; then run the integration test:

   ```sh
   docker run --rm -v "$PWD":/workspace -w /workspace \
       solaxpico-devcontainer:latest \
       python scripts/test_integration.py --host <pico-ip>
   ```

The bridge IP is shown in the serial log (`connected: 10.x.x.x`).

## Configuration

| What | Where | Default |
|---|---|---|
| Wi-Fi credentials | `wifi_config.py` (`WIFI_SSID`, `WIFI_PASS`) | — (gitignored) |
| Remote debugging (WebREPL) | `wifi_config.py` (`WEBREPL_PASS`) | off (unset/empty) |
| Serial device | Makefile variable `PICO_SERIAL` | `/dev/ttyACM0` |
| BOOTSEL mount point | `RPI_MOUNT` (only if auto-detection fails) | auto |
| UART parameters | `src/main.py` constants | 19200 8N1, UART0 |
| TCP port / client limit | `src/main.py` constants | 502 / 4 |
| Watchdog | `src/main.py` (`ENABLE_WATCHDOG`, `WDT_TIMEOUT_MS`) | on / 8000 ms |

`wifi_config.py` sits unencrypted on the Pico's filesystem. That is accepted
for a LAN device; anyone with the Wi-Fi password and physical access can read
it out over USB.

## Testing

- **Unit tests** (CPython, no device needed): `make test`. On machines
  without Python/pytest: `make test_dockerized` runs the same 55 tests inside
  the devcontainer image (built on demand from `.devcontainer/Dockerfile`).
- **Integration test** (`scripts/test_integration.py`, needs the deployed
  bridge and ideally the wired inverter): TCP connect, holding-register and
  input-register reads, 10× sequential requests, and a ghost-slave timeout
  check. Run it where pymodbus is available — the devcontainer image ships
  pymodbus:

  ```sh
  docker run --rm -v "$PWD":/workspace -w /workspace \
      solaxpico-devcontainer:latest \
      python scripts/test_integration.py --host <pico-ip>
  ```

  With the inverter wired, all 5 tests pass; without it, register reads
  report clean `[FAIL]`s (timeouts) while TCP and the ghost-slave test pass.

## Remote debugging (WebREPL)

For live inspection without USB access, enable MicroPython's **WebREPL**:

1. In `wifi_config.py`, set `WEBREPL_PASS = "..."` (non-empty, not the
   placeholder). Leave it unset to keep WebREPL off.
2. Deploy (`make deploy` / `make deploy_docker`) and reboot the Pico.
3. Connect to `ws://<pico-ip>:8266/` with a WebREPL client (for example the
   browser client at https://micropython.org/webrepl/).

The REPL runs alongside the bridge and lets you inspect state or run snippets
(e.g. `import gc; gc.mem_free()`, or probe the UART/RTU objects if you adapt
the code to expose them). It does **not** stream the existing USB-serial log
history — `print()` output still goes to the USB serial console. The WebREPL
password is stored in `wifi_config.py` on the device like the Wi-Fi credentials.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `mpremote not found` | Use `make deploy_docker`, or install mpremote (`pip install mpremote`). |
| `serial device /dev/ttyACM0 not found` | Pico unplugged, or in BOOTSEL mode. Re-plug and let MicroPython boot. |
| Serial permission denied (devcontainer) | Reconnect the container — `postStartCommand` runs `.devcontainer/fix-serial-access.sh`; from the host, `sudo chmod a+rw /dev/ttyACM0` works as a fallback. |
| `RPI-RP2 mass-storage device not found` | Hold BOOTSEL while plugging in. If the mount is elsewhere, pass `RPI_MOUNT=/path/to/RPI-RP2`. |
| Firmware: `bad TX pin` | GP0/GP1 are **UART0** pins on the RP2040 — the code must use `UART(0)`, not `UART(1)`. Current code is correct; this bit us once. |
| `name 'TimeoutError' isn't defined` in logs | MicroPython lacks the builtin; code now uses `RTUTimeoutError` from `modbus_bridge.py`. Current code is correct. |
| Bridge boots, but no Modbus response | Check RS485 A/B wiring and the inverter's COM cable. The adapter's TX LED should blink on each request. If it never blinks, TXD/RXD may be swapped (swap the GP0/GP1 leads to test). |
| `Wi-Fi not recoverable` + 3 blinks + reset | Wrong credentials, or the SSID is 5 GHz-only. Check `wifi_config.py`. |
| Board keeps rebooting in a loop | Watch for the `[main] FATAL:` line in the serial log; it names the reason (Wi-Fi or repeated bridge errors). Modbus timeouts alone never trigger this. |

## Deployment checklist (production swap)

1. Read out the bridge IP from the serial log and reserve it via DHCP.
2. Confirm all 5 integration tests pass with the wired inverter.
3. Let the bridge run a full day unattended; check the serial/heartbeat logs
   (`[main] heartbeat: ...` every 60 s) for memory drift (`mem_free` stable).
4. Power off, move the Pico from USB to the Mini-560 (VSYS), power up from
   the inverter, repeat the integration test over Wi-Fi.
5. Keep the old Pi Zero W + mbusd ready as rollback.

**Rollback:** power off, disconnect the RJ45 from the Pico/adapter setup and
re-plug it into the Pi Zero W, boot it, done — the mbusd setup is unchanged.
Code-level rollback (same hardware): `git checkout <previous-commit>` and
`make deploy`.

## Repository layout

```
├── Makefile                  firmware / deploy / deploy_docker / test / test_dockerized
├── src/                      MicroPython code (deployed to the Pico)
├── tests/                    CPython pytest suite (55 tests)
├── scripts/                  thin Make wrappers + pymodbus integration test
├── doc/hardware.md           full wiring reference, schematics, bring-up notes
├── case/solaxpico.FCStd      FreeCAD project for the 3D-printed case
├── .devcontainer/            Docker dev environment (incl. serial-access fix)
├── wifi_config.example.py    Wi-Fi credential template
└── wifi_config.py            your credentials (gitignored, create yourself)
```
