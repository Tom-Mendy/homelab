#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="endfield-checkin:latest"
ENV_FILE="${1:-.env}"

echo "[1/2] Build image: ${IMAGE_NAME}"
docker build -t "$IMAGE_NAME" .

echo "[2/2] Run container"
if [[ -f "$ENV_FILE" ]]; then
  docker run --rm --env-file "$ENV_FILE" "$IMAGE_NAME"
else
  echo "Env file '$ENV_FILE' not found."
  echo "Copy .env.example to .env and fill your values, or pass an env file path as first arg."
  exit 1
fi
