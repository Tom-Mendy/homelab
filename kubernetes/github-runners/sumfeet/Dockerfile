# syntax=docker/dockerfile:1.7

FROM ghcr.io/actions/actions-runner:2.337.0@sha256:e5496277be5d09bc968b3d64911b74e219ac4a3f2edce956a3ecf9271bea1ef4

USER root

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git-lfs \
    && git lfs version \
    && rm -rf /var/lib/apt/lists/*

USER runner

LABEL org.opencontainers.image.title="SumFeet GitHub Actions runner" \
      org.opencontainers.image.description="ARC runner with Git LFS" \
      org.opencontainers.image.source="https://forgejo.tom-mendy.com/Tom-Mendy/homelab"
