#!/usr/bin/env python3
"""Check token-bound device selection without sending Matrix messages."""

import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch


LAUNCHER = Path(__file__).resolve().parents[1] / (
    "kubernetes/coder/workspace-templates/hermes-personal/launch-gateway.py"
)
spec = importlib.util.spec_from_file_location("launch_gateway", LAUNCHER)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class MatrixIdentityTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "MATRIX_HOMESERVER": "https://matrix.example.test/",
            "MATRIX_ACCESS_TOKEN": "test-token",
            "MATRIX_USER_ID": "@bot:matrix.example.test",
        }

    def resolve(self, identity):
        with patch.object(launcher.urllib.request, "urlopen") as request:
            request.return_value.__enter__.return_value = io.StringIO(json.dumps(identity))
            device = launcher.matrix_device_id(self.env)
            self.assertEqual(request.call_args.args[0].full_url,
                             "https://matrix.example.test/_matrix/client/v3/account/whoami")
            self.assertEqual(request.call_args.kwargs["timeout"], 30)
            return device

    def test_resolves_device_when_no_override_is_configured(self):
        self.assertEqual(self.resolve({"user_id": self.env["MATRIX_USER_ID"],
                                       "device_id": "existing-device"}), "existing-device")

    def test_uses_new_token_identity_after_rotation(self):
        self.assertEqual(self.resolve({"user_id": self.env["MATRIX_USER_ID"],
                                       "device_id": "rotated-device"}), "rotated-device")

    def test_rejects_mismatched_user(self):
        with self.assertRaises(ValueError):
            self.resolve({"user_id": "@other:matrix.example.test", "device_id": "device"})

    def test_rejects_missing_device(self):
        with self.assertRaises(ValueError):
            self.resolve({"user_id": self.env["MATRIX_USER_ID"]})

    def test_rejects_stale_override(self):
        self.env["MATRIX_DEVICE_ID"] = "stale-device"
        with self.assertRaises(ValueError):
            self.resolve({"user_id": self.env["MATRIX_USER_ID"], "device_id": "current-device"})


if __name__ == "__main__":
    unittest.main()
