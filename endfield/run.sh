#!/usr/bin/env bash

set -euo pipefail

# Ensure relative paths work regardless of where run.sh is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export ENDFIELD_CRED='REMOVED_ENDFIELD_SECRET'
export ENDFIELD_SK_GAME_ROLE='REMOVED_ENDFIELD_SECRET'
export ENDFIELD_PLATFORM='3'
export ENDFIELD_VNAME='1.0.0'
export ENDFIELD_ACCOUNT_NAME='REMOVED_ENDFIELD_SECRET'
export DISCORD_WEBHOOK_URL='REMOVED_ENDFIELD_SECRET'
export DISCORD_USER_ID='REMOVED_DISCORD_ID'

node endfield_test.js