FROM nousresearch/hermes-agent@sha256:b6c019227889e6675424a2b6223b2cafdd36bf7d1048d1ddd8e043b880d6cc0f

USER root

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        bash \
        build-essential \
        ca-certificates \
        chromium \
        curl \
        dbus-x11 \
        dnsutils \
        fd-find \
        file \
        fonts-dejavu \
        fonts-noto-color-emoji \
        git \
        jq \
        less \
        libffi-dev \
        libssl-dev \
        netcat-openbsd \
        novnc \
        openssh-client \
        pkg-config \
        procps \
        python3-dev \
        python3-venv \
        ripgrep \
        rsync \
        shellcheck \
        tigervnc-standalone-server \
        tree \
        unzip \
        websockify \
        xfce4 \
        xfce4-terminal \
        xfonts-base \
        x11-xserver-utils \
        zip \
    && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -o 10000 -g 10000 /opt/data /opt/data/.vnc /opt/data/.config /opt/novnc \
    && cp -a /usr/share/novnc/. /opt/novnc/ \
    && cp /usr/share/novnc/vnc.html /opt/novnc/index.html \
    && chown -R 10000:10000 /opt/novnc

COPY start-desktop.sh /usr/local/bin/start-desktop.sh
RUN chmod 0755 /usr/local/bin/start-desktop.sh \
    && printf '%s\n' \
        '#!/bin/sh' \
        'exec /usr/bin/chromium --no-sandbox "$@"' \
        > /usr/local/bin/chromium-workspace \
    && chmod 0755 /usr/local/bin/chromium-workspace \
    && if [ -f /usr/share/applications/chromium.desktop ]; then \
         sed -i -E 's|^Exec=([^ ]*chromium)(.*)$|Exec=/usr/local/bin/chromium-workspace\2|' \
           /usr/share/applications/chromium.desktop; \
       fi

ENV HOME=/opt/data \
    SHELL=/usr/bin/bash \
    USER=tmendy \
    DISPLAY=:1 \
    VNC_GEOMETRY=1920x1080 \
    VNC_DEPTH=24

USER 10000:10000
WORKDIR /opt/data
