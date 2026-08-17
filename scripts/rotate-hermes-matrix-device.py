#!/usr/bin/env python3
"""Mint a Hermes token on a fresh Matrix device through a port-forward."""

import json
import os
import sys
import urllib.parse
import urllib.request

BASE_URL = "http://127.0.0.1:8008"
USER_ID = "@hermes-bot:matrix.tom-mendy.com"


def admin_login_url(user_id):
    return f"{BASE_URL}/_synapse/admin/v1/users/{urllib.parse.quote(user_id, safe='')}/login"


if sys.argv[1:] == ["--self-test"]:
    assert admin_login_url(USER_ID).endswith(
        "/%40hermes-bot%3Amatrix.tom-mendy.com/login"
    )
    raise SystemExit(0)

if len(sys.argv) != 3:
    raise SystemExit(f"usage: {sys.argv[0]} ADMIN_TOKEN_FILE TOKEN_FILE")

admin_token_file, token_file = sys.argv[1:]
if os.path.lexists(token_file):
    raise SystemExit(f"refusing to overwrite {token_file}")
if os.stat(admin_token_file).st_mode & 0o077:
    raise SystemExit(f"{admin_token_file} must not be accessible by group or others")

admin_token = open(admin_token_file, "r", encoding="utf-8").read().strip()
if not admin_token:
    raise SystemExit(f"{admin_token_file} is empty")

request = urllib.request.Request(
    admin_login_url(USER_ID),
    data=b"{}",
    headers={
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    },
)
with urllib.request.urlopen(request, timeout=10) as response:
    token = json.load(response).get("access_token")
if not token:
    raise SystemExit("Tuwunel did not return an access token")

request = urllib.request.Request(
    f"{BASE_URL}/_matrix/client/v3/account/whoami",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(request, timeout=10) as response:
    identity = json.load(response)
if identity.get("user_id") != USER_ID or not identity.get("device_id"):
    raise SystemExit("the new token does not identify the expected user and device")

fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as output:
    output.write(token)
print(f"created fresh Matrix device {identity['device_id']}; token saved to {token_file}")
