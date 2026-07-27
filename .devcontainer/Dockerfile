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

ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create non-root developer user with serial device access
RUN groupadd -g $USER_GID $USERNAME \
    && useradd -m -u $USER_UID -g $USERNAME -G dialout,plugdev $USERNAME \
    && mkdir -p /workspace \
    && chown $USERNAME:$USERNAME /workspace

# Pre-create .roo and zooCode globalStorage directories with correct ownership
# These are targets for bind mounts from the host; pre-creating ensures correct permissions
RUN mkdir -p /home/$USERNAME/.roo/skills \
    /home/$USERNAME/.vscode-server/data/User/globalStorage/zoocodeorganization.zoo-code/settings \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME/.roo \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME/.vscode-server

USER $USERNAME
WORKDIR /workspace

# Default command
CMD ["sleep", "infinity"]
