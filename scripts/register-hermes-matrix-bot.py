#!/usr/bin/env python3
"""Register the local Hermes Matrix bot through a localhost port-forward."""

import hashlib
import hmac
import json
import os
import secrets
import sys
import urllib.request

URL = "http://127.0.0.1:8008/_synapse/admin/v1/register"
USERNAME = "hermes-bot"


def registration_mac(secret, nonce, password):
    message = "\0".join((nonce, USERNAME, password, "notadmin")).encode()
    return hmac.new(secret, message, hashlib.sha1).hexdigest()


if sys.argv[1:] == ["--self-test"]:
    assert registration_mac(b"secret", "nonce", "password") == (
        "4644a3765159aba340db69852f301a4013ab4951"
    )
    raise SystemExit(0)

if len(sys.argv) != 3:
    raise SystemExit(f"usage: {sys.argv[0]} SECRET_FILE TOKEN_FILE")
if os.path.lexists(sys.argv[2]):
    raise SystemExit(f"refusing to overwrite {sys.argv[2]}")

secret = open(sys.argv[1], "rb").read().strip()
if len(secret) < 32:
    raise SystemExit("registration secret must contain at least 32 bytes")

with urllib.request.urlopen(URL, timeout=10) as response:
    nonce = json.load(response)["nonce"]

password = secrets.token_urlsafe(48)
body = json.dumps(
    {
        "nonce": nonce,
        "username": USERNAME,
        "password": password,
        "admin": False,
        "inhibit_login": False,
        "mac": registration_mac(secret, nonce, password),
    }
).encode()
request = urllib.request.Request(
    URL, data=body, headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(request, timeout=10) as response:
    token = json.load(response).get("access_token")
if not token:
    raise SystemExit("registration succeeded without returning an access token")

fd = os.open(sys.argv[2], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as token_file:
    token_file.write(token)
print(f"registered @{USERNAME}:matrix.tom-mendy.com; token saved to {sys.argv[2]}")
