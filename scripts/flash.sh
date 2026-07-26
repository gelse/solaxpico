#!/bin/bash
#
# flash.sh — Flash MicroPython .uf2 to Raspberry Pi Pico W
#
# Usage:
#   ./scripts/flash.sh [path/to/firmware.uf2]
#
# If no path is given, the script prompts for one.
# The Pico must be in BOOTSEL mode (hold BOOTSEL, connect USB).
#
# Options:
#   -h, --help    Show this help message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

print_help() {
    sed -ne '/^#/!q;s/.\{1,2\}//;1,4d;p' "${BASH_SOURCE[0]}"
    exit 0
}

# Parse arguments
if [[ $# -gt 0 ]]; then
    case "$1" in
        -h|--help) print_help ;;
        *) FIRMWARE="$1" ;;
    esac
fi

# Prompt for firmware if not provided
if [[ -z "${FIRMWARE:-}" ]]; then
    echo "Pico W Firmware Flasher"
    echo "======================="
    echo ""
    echo "Enter path to .uf2 firmware file, or leave empty for default:"
    read -r -p "Firmware path: " FIRMWARE
fi

if [[ -z "${FIRMWARE:-}" ]]; then
    echo "No firmware path provided. Exiting."
    exit 1
fi

if [[ ! -f "$FIRMWARE" ]]; then
    echo "Error: Firmware file not found: $FIRMWARE"
    exit 1
fi

if [[ "${FIRMWARE##*.}" != "uf2" ]]; then
    echo "Warning: File is not a .uf2 file. Continue anyway? [y/N]"
    read -r confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo ""
echo "Put the Pico W into BOOTSEL mode:"
echo "  1. Hold the BOOTSEL button on the Pico W"
echo "  2. Connect USB (or press RESET while holding BOOTSEL)"
echo "  3. Release BOOTSEL after connecting"
echo ""
echo "Waiting for Pico in BOOTSEL mode..."

# Wait for mass storage device to appear
RPI_MOUNT=""
for _ in {1..30}; do
    # Try common mount points
    for mount in /media/*/RPI-RP2 /run/media/*/RPI-RP2 /mnt/RPI-RP2; do
        if [[ -d "$mount" ]]; then
            RPI_MOUNT="$mount"
            break 2
        fi
    done
    sleep 1
done

if [[ -z "$RPI_MOUNT" ]]; then
    echo ""
    echo "Could not find RPI-RP2 mount point."
    echo "Try mounting manually:"
    echo "  sudo mount /dev/sda1 /mnt"
    echo "Then re-run this script with:"
    echo "  FIRMWARE_MOUNT=/mnt ./scripts/flash.sh"
    echo ""
    echo "Alternatively, copy the firmware manually:"
    echo "  cp $FIRMWARE /path/to/RPI-RP2/"
    exit 1
fi

echo "Pico found at: $RPI_MOUNT"
echo "Flashing $FIRMWARE ..."

cp "$FIRMWARE" "$RPI_MOUNT/"

echo ""
echo "Flash complete! The Pico will reboot automatically."
echo ""
echo "After reboot, verify with:"
echo "  ls /dev/ttyACM*"
echo "  screen /dev/ttyACM0 115200"
