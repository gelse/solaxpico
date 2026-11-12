#!/usr/bin/env bash
# deploy.sh — thin wrapper around `make deploy`.
#
# Entry point for the VSCode tasks "Deploy Code" / "Deploy & Reset". All logic
# (serial checks, mpremote copy, reset) lives in the Makefile.
#
# Usage:
#   scripts/deploy.sh             # deploy only
#   scripts/deploy.sh --monitor   # deploy, then attach the serial REPL
#
# The serial device defaults to /dev/ttyACM0 and can be overridden via the
# PICO_SERIAL environment variable (same as `make deploy`).
# Exit the REPL with Ctrl+] when using --monitor.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERIAL="${PICO_SERIAL:-/dev/ttyACM0}"

if [ "${1:-}" = "--monitor" ]; then
    make -C "$SCRIPT_DIR/.." deploy
    exec mpremote connect "$SERIAL"
elif [ $# -gt 0 ]; then
    echo "Error: unknown argument '$1'. Usage: deploy.sh [--monitor]" >&2
    exit 2
else
    exec make -C "$SCRIPT_DIR/.." deploy
fi
