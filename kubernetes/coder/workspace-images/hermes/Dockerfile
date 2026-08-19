FROM nousresearch/hermes-agent@sha256:b6c019227889e6675424a2b6223b2cafdd36bf7d1048d1ddd8e043b880d6cc0f

USER root

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        bash \
        build-essential \
        ca-certificates \
        curl \
        dnsutils \
        fd-find \
        file \
        git \
        jq \
        less \
        libffi-dev \
        libssl-dev \
        netcat-openbsd \
        openssh-client \
        pkg-config \
        procps \
        python3-dev \
        python3-venv \
        ripgrep \
        rsync \
        shellcheck \
        tree \
        unzip \
        zip \
    && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
    && rm -rf /var/lib/apt/lists/*

ENV HOME=/opt/data \
    SHELL=/usr/bin/bash

USER 10000:10000
WORKDIR /opt/data
