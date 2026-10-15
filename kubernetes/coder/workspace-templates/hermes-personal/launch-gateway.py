"""Resolve the token-bound Matrix device before opening the persistent crypto store."""

import json
import os
import sys
import urllib.error
import urllib.request


def matrix_device_id(environ):
    request = urllib.request.Request(
        environ["MATRIX_HOMESERVER"].rstrip("/")
        + "/_matrix/client/v3/account/whoami",
        headers={"Authorization": "Bearer " + environ["MATRIX_ACCESS_TOKEN"]},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        identity = json.load(response)
    if identity.get("user_id") != environ["MATRIX_USER_ID"]:
        raise ValueError("Matrix token belongs to an unexpected user")
    device_id = identity.get("device_id")
    if not isinstance(device_id, str) or not device_id:
        raise ValueError("Matrix token has no device identity")
    configured = environ.get("MATRIX_DEVICE_ID")
    if configured and configured != device_id:
        raise ValueError("Configured Matrix device differs from the token identity")
    return device_id


def main():
    try:
        os.environ["MATRIX_DEVICE_ID"] = matrix_device_id(os.environ)
    except (KeyError, ValueError, urllib.error.URLError, TimeoutError) as error:
        # Do not expose tokens or response bodies in the supervisor log.
        print(f"Matrix identity lookup failed ({type(error).__name__}); retrying.",
              file=sys.stderr, flush=True)
        return 1
    print(f"Matrix gateway device: {os.environ['MATRIX_DEVICE_ID']}", flush=True)
    os.execv("/opt/hermes/bin/hermes", ["hermes", "gateway", "run"])


if __name__ == "__main__":
    sys.exit(main())
