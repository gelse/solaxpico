# Makefile for solaxpico (Pico W Modbus gateway)
#
# Default target prints usage information.

SHELL := /bin/bash

BOARD         ?= RPI_PICO_W
FIRMWARE_URL  ?= https://micropython.org/download/$(BOARD)/$(BOARD)-latest.uf2
FIRMWARE_DIR  ?= firmware
FIRMWARE_FILE ?= $(FIRMWARE_DIR)/$(BOARD)-latest.uf2

# Serial device for a Pico running MicroPython (used by deploy).
PICO_SERIAL   ?= /dev/ttyACM0

# Python interpreter for the CPython test runs.
PY            ?= python3

# Docker image used by test_dockerized; built from .devcontainer/Dockerfile
# so host and CI runners share the same image definition.
DEVCONTAINER_IMAGE ?= solaxpico-devcontainer:latest

# Optional: override if auto-detection does not find the BOOTSEL drive.
# Example: make firmware RPI_MOUNT=/run/media/$$USER/RPI-RP2
RPI_MOUNT     ?=

.PHONY: help firmware deploy deploy_docker clean-firmware test test_dockerized

help: ## Show this help message (default)
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ { \
		printf "  %-18s %s\n", $$1, $$2 \
	}' $(MAKEFILE_LIST)

firmware: $(FIRMWARE_FILE) ## Download (if needed) and flash MicroPython firmware to the Pico W (BOOTSEL mode)
	@set -euo pipefail; \
	mountpoint="$(RPI_MOUNT)"; \
	user="$${USER:-$$(id -un 2>/dev/null || echo unknown)}"; \
	if [ -z "$$mountpoint" ]; then \
		for p in \
			"/run/media/$$user/RPI-RP2" \
			"/media/$$user/RPI-RP2" \
			"/media/RPI-RP2" \
			"/mnt/RPI-RP2" \
			"/Volumes/RPI-RP2"; \
		do \
			if [ -d "$$p" ]; then mountpoint="$$p"; break; fi; \
		done; \
	fi; \
	if [ -z "$$mountpoint" ]; then \
		echo "Error: RPI-RP2 mass-storage device not found." >&2; \
		echo "Put the Pico W into BOOTSEL mode (hold BOOTSEL while connecting USB)," >&2; \
		echo "ensure it is mounted, or pass RPI_MOUNT=/path/to/RPI-RP2." >&2; \
		exit 1; \
	fi; \
	echo "Flashing MicroPython firmware to $$mountpoint ..."; \
	cp "$(FIRMWARE_FILE)" "$$mountpoint/"; \
	sync; \
	echo "Done. The Pico will reboot automatically after the copy completes."

deploy: ## Deploy solution code, configuration, and service stub to the Pico (MicroPython over serial)
	@set -euo pipefail; \
	if ! command -v mpremote >/dev/null 2>&1; then \
		echo "Error: mpremote not found. Install it (e.g. pip install mpremote) or run inside the devcontainer." >&2; \
		exit 1; \
	fi; \
	if [ ! -e "$(PICO_SERIAL)" ]; then \
		echo "Error: serial device $(PICO_SERIAL) not found." >&2; \
		echo "Ensure the Pico is connected with MicroPython running, or set PICO_SERIAL=/dev/ttyACM0." >&2; \
		exit 1; \
	fi; \
	if [ ! -f wifi_config.py ]; then \
		echo "Error: wifi_config.py not found." >&2; \
		echo "Copy wifi_config.example.py to wifi_config.py and set your credentials." >&2; \
		exit 1; \
	fi; \
	echo "Deploying to $(PICO_SERIAL) ..."; \
	mpremote connect "$(PICO_SERIAL)" fs cp src/boot.py :boot.py; \
	mpremote connect "$(PICO_SERIAL)" fs cp src/main.py :main.py; \
	mpremote connect "$(PICO_SERIAL)" fs cp src/modbus_bridge.py :modbus_bridge.py; \
	mpremote connect "$(PICO_SERIAL)" fs cp wifi_config.py :wifi_config.py; \
	echo "Resetting Pico to start the deployed service ..."; \
	mpremote connect "$(PICO_SERIAL)" reset; \
	echo "Done. Bridge deployed (Wi-Fi + Modbus TCP on port 502)."

$(FIRMWARE_FILE):
	@mkdir -p "$(FIRMWARE_DIR)"
	@echo "Downloading MicroPython firmware from $(FIRMWARE_URL) ..."
	@if command -v curl >/dev/null 2>&1; then \
		curl -fL --retry 3 -o "$(FIRMWARE_FILE)" "$(FIRMWARE_URL)"; \
	elif command -v wget >/dev/null 2>&1; then \
		wget -O "$(FIRMWARE_FILE)" "$(FIRMWARE_URL)"; \
	else \
		python3 -c "import urllib.request; urllib.request.urlretrieve('$(FIRMWARE_URL)', '$(FIRMWARE_FILE)')"; \
	fi
	@echo "Firmware saved to $(FIRMWARE_FILE)"

deploy_docker: ## Deploy to the Pico using mpremote inside the devcontainer image (for hosts without mpremote)
	@set -euo pipefail; \
	if ! command -v docker >/dev/null 2>&1; then \
		echo "Error: docker not found." >&2; \
		exit 1; \
	fi; \
	if ! docker image inspect "$(DEVCONTAINER_IMAGE)" >/dev/null 2>&1; then \
		echo "Devcontainer image $(DEVCONTAINER_IMAGE) not found — building it from .devcontainer/Dockerfile ..."; \
		docker build -t "$(DEVCONTAINER_IMAGE)" .devcontainer/; \
	fi; \
	if [ ! -e "$(PICO_SERIAL)" ]; then \
		echo "Error: serial device $(PICO_SERIAL) not found." >&2; \
		echo "Ensure the Pico is connected with MicroPython running." >&2; \
		exit 1; \
	fi; \
	if [ ! -f wifi_config.py ]; then \
		echo "Error: wifi_config.py not found." >&2; \
		echo "Copy wifi_config.example.py to wifi_config.py and set your credentials." >&2; \
		exit 1; \
	fi; \
	DEV_GID=$$(stat -c %g "$(PICO_SERIAL)"); \
	echo "Deploying to $(PICO_SERIAL) via devcontainer image ..."; \
	docker run --rm -v "$$PWD":/workspace -w /workspace \
		--device "$(PICO_SERIAL)" --group-add "$$DEV_GID" \
		"$(DEVCONTAINER_IMAGE)" sh -c '\
			mpremote connect '"$(PICO_SERIAL)"' fs cp src/boot.py :boot.py && \
			mpremote connect '"$(PICO_SERIAL)"' fs cp src/main.py :main.py && \
			mpremote connect '"$(PICO_SERIAL)"' fs cp src/modbus_bridge.py :modbus_bridge.py && \
			mpremote connect '"$(PICO_SERIAL)"' fs cp wifi_config.py :wifi_config.py && \
			mpremote connect '"$(PICO_SERIAL)"' reset'; \
	echo "Done. Bridge deployed (Wi-Fi + Modbus TCP on port 502)."

clean-firmware: ## Remove downloaded MicroPython firmware files
	rm -rf "$(FIRMWARE_DIR)"

test: ## Run the unit tests with CPython (pytest)
	@set -euo pipefail; \
	if ! command -v "$(PY)" >/dev/null 2>&1; then \
		echo "Error: $(PY) not found. Use 'make test_dockerized' on systems without CPython." >&2; \
		exit 1; \
	fi; \
	if ! "$(PY)" -m pytest --version >/dev/null 2>&1; then \
		echo "Error: pytest is not available for $(PY). Install it (pip install pytest) or use 'make test_dockerized'." >&2; \
		exit 1; \
	fi; \
	"$(PY)" -m pytest tests/ -v

test_dockerized: ## Run the unit tests inside the devcontainer image via docker (for CI runners without CPython)
	@set -euo pipefail; \
	if ! command -v docker >/dev/null 2>&1; then \
		echo "Error: docker not found." >&2; \
		exit 1; \
	fi; \
	if ! docker image inspect "$(DEVCONTAINER_IMAGE)" >/dev/null 2>&1; then \
		echo "Devcontainer image $(DEVCONTAINER_IMAGE) not found — building it from .devcontainer/Dockerfile ..."; \
		docker build -t "$(DEVCONTAINER_IMAGE)" .devcontainer/; \
	fi; \
	docker run --rm -v "$$PWD":/workspace -w /workspace "$(DEVCONTAINER_IMAGE)" \
		python -m pytest tests/ -v

.DEFAULT_GOAL := help
