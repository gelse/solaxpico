#!/bin/bash
#
# deploy.sh — Deploy Python source files to Raspberry Pi Pico W via mpremote
#
# Usage:
#   ./scripts/deploy.sh [device]
#
# Copies all source files (boot.py, main.py, modbus_bridge.py) to
# the connected Pico W using mpremote.
#
# Options:
#   device    Serial device path (default: /dev/ttyACM0)
#   -h, --help    Show this help message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

SRC_DIR="$PROJECT_DIR/src"

print_help() {
    sed -ne '/^#/!q;s/.\{1,2\}//;1,4d;p' "${BASH_SOURCE[0]}"
    exit 0
}

# Parse arguments
DEVICE="${1:-/dev/ttyACM0}"
if [[ "$DEVICE" == "-h" || "$DEVICE" == "--help" ]]; then
    print_help
fi

if [[ ! -e "$DEVICE" ]]; then
    echo "Warning: Device $DEVICE not found."
    echo "Make sure the Pico is connected."
    echo "Continue anyway? [y/N]"
    read -r confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo "Deploying to Pico W at $DEVICE ..."
echo ""

# Files to deploy (in order)
FILES=(
    "boot.py"
    "main.py"
    "modbus_bridge.py"
)

for FILE in "${FILES[@]}"; do
    SRC_PATH="$SRC_DIR/$FILE"
    if [[ ! -f "$SRC_PATH" ]]; then
        echo "Warning: $SRC_PATH not found, skipping."
        continue
    fi
    echo "Copying $FILE ..."
    mpremote connect "$DEVICE" fs cp "$SRC_PATH" ":$FILE"
done

echo ""
echo "Deploy complete!"
echo ""
echo "The Pico will run the new code on next boot."
echo "To restart now, run:"
echo "  mpremote connect $DEVICE reset"
echo ""
echo "To view serial output:"
echo "  screen $DEVICE 115200"
