"""Regression tests for change-only NFS alert notifications."""
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "nfs-alert-watchdog.py"


class WatchdogTests(unittest.TestCase):
    def test_only_firing_nfs_rules_are_forwarded(self):
        spec = importlib.util.spec_from_file_location("watchdog", PATH)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        alerts = [
            {"state": "firing", "labels": {"alertname": "NFSProbeSlow", "node": "node3"}},
            {"state": "pending", "labels": {"alertname": "NFSProbeFailed", "node": "node2"}},
            {"state": "firing", "labels": {"alertname": "OtherApplicationWarning"}},
        ]
        self.assertEqual(mod.firing_nfs_alerts(alerts), ["node3: NFSProbeSlow"])

    def test_alerts_only_after_two_failed_observations_and_reports_recovery(self):
        self.assertTrue(PATH.is_file(), "watchdog is missing")
        spec = importlib.util.spec_from_file_location("watchdog", PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        state, message = mod.transition({}, "node3: TEST_STATEID=4000/s")
        self.assertEqual(message, "")
        state, message = mod.transition(state, "node3: TEST_STATEID=4000/s")
        self.assertIn("NFS", message)
        state, message = mod.transition(state, "node3: TEST_STATEID=5000/s")
        self.assertEqual(message, "")
        state, message = mod.transition(state, "")
        self.assertIn("rétabli", message)
        state, message = mod.transition(state, "")
        self.assertEqual(message, "")


if __name__ == "__main__":
    unittest.main()
