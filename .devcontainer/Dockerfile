# syntax=docker/dockerfile:1
# Pico W Modbus Development Container
# Base: python:3.12-slim (Debian Bookworm)
# Tools: mbpoll (apt), picotool (apt), mpremote, pymodbus

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmodbus5 \
    libusb-1.0-0 \
    mbpoll \
    picotool \
    screen \
    usbutils \
    minicom \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    mpremote \
    pymodbus \
    pytest \
    flake8

# Create non-root developer user with serial device access
RUN groupadd -g 1000 developer \
    && useradd -m -u 1000 -g developer -G dialout,plugdev developer \
    && mkdir -p /workspace \
    && chown developer:developer /workspace

# Pre-create .roo and zooCode globalStorage directories with correct ownership
# These are targets for bind mounts from the host; pre-creating ensures correct permissions
RUN mkdir -p /home/$USERNAME/.roo/skills \
    /home/$USERNAME/.vscode-server/data/User/globalStorage/zoocodeorganization.zoo-code/settings \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME/.roo \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME/.vscode-server

USER developer
WORKDIR /workspace

# Default command
CMD ["sleep", "infinity"]
