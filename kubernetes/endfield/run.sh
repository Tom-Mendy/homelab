#!/usr/bin/env bash

set -euo pipefail

# Ensure relative paths work regardless of where run.sh is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Optional: load variables from .env in this directory.
if [[ -f .env ]]; then
	set -a
	# shellcheck disable=SC1091
	source .env
	set +a
fi

if [[ -z "${ENDFIELD_CRED:-}" || -z "${ENDFIELD_SK_GAME_ROLE:-}" ]]; then
	echo "Missing ENDFIELD_CRED or ENDFIELD_SK_GAME_ROLE."
	echo "Set env vars or create .env from .env.example."
	exit 1
fi

node endfield_test.js