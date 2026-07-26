# syntax=docker/dockerfile:1
# Pico W Modbus Development Container
# Base: python:3.12-slim (Debian Bookworm)
# Tools: mbpoll (built from source), picotool (pre-built binary), mpremote, pymodbus

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libmodbus-dev \
    libusb-1.0-0-dev \
    pkg-config \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Build mbpoll from source ---
RUN git clone --depth 1 https://github.com/epsilonrt/mbpoll.git /tmp/mbpoll \
    && mkdir -p /tmp/mbpoll/build \
    && cd /tmp/mbpoll/build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release \
    && make -j"$(nproc)" \
    && make install \
    && rm -rf /tmp/mbpoll

# --- Download picotool pre-built binary ---
RUN set -eux; \
    arch="$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')"; \
    url="https://github.com/raspberrypi/picotool/releases/latest/download/picotool-linux-${arch}.tar.gz"; \
    wget -qO /tmp/picotool.tar.gz "${url}"; \
    tar -xzf /tmp/picotool.tar.gz -C /usr/local/bin/; \
    rm -f /tmp/picotool.tar.gz

# --- Final runtime image ---
FROM python:3.12-slim

COPY --from=builder /usr/local/bin/mbpoll /usr/local/bin/mbpoll
COPY --from=builder /usr/local/bin/picotool /usr/local/bin/picotool

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmodbus5 \
    libusb-1.0-0 \
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

USER developer
WORKDIR /workspace

# Default command
CMD ["sleep", "infinity"]
