#!/usr/bin/env bash
# flash.sh — thin wrapper around `make firmware`.
#
# Entry point for the VSCode task "Flash Pico". All logic (download, BOOTSEL
# detection, copy) lives in the Makefile; arguments are forwarded to make,
# e.g.:
#
#   scripts/flash.sh RPI_MOUNT=/run/media/$USER/RPI-RP2
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec make -C "$SCRIPT_DIR/.." firmware "$@"
