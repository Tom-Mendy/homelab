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
  # Source shell-style env file so quoted values are interpreted correctly.
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a

  docker run --rm \
    -e ENDFIELD_CRED \
    -e ENDFIELD_SK_GAME_ROLE \
    -e ENDFIELD_PLATFORM \
    -e ENDFIELD_VNAME \
    -e ENDFIELD_ACCOUNT_NAME \
    -e ENABLE_DISCORD_NOTIFY \
    -e DISCORD_WEBHOOK_URL \
    -e DISCORD_USER_ID \
    "$IMAGE_NAME"
else
  echo "Env file '$ENV_FILE' not found."
  echo "Create .env with shell syntax (quoted values allowed), or pass an env file path as first arg."
  exit 1
fi
