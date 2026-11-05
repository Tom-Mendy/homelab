"""Regression tests for change-only NFS alert notifications."""
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "nfs-alert-watchdog.py"


class WatchdogTests(unittest.TestCase):
    def test_recovery_requires_successful_fresh_probes_even_without_firing_rules(self):
        import io
        import json
        import urllib.parse
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("watchdog", PATH)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        def response(url, timeout):
            if url.endswith("/api/v1/alerts"):
                data = {"alerts": []}
            else:
                query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["query"][0]
                values = probe_values if "nfs_probe_success" in query else {"node2": "0", "node3": "0"}
                data = {"result": [{"metric": {"node": node}, "value": [100, value]}
                                   for node, value in values.items()]}
            return io.BytesIO(json.dumps({"status": "success", "data": data}).encode())
        for probe_values, expected in (
            ({"node2": "0", "node3": "1"}, "node2: NFSProbeFailed"),
            ({"node2": "NaN", "node3": "1"}, "node2: NFSProbeFailed"),
            ({}, "sondes NFS absentes"),
            ({"node2": "1", "node3": "1"}, ""),
        ):
            with self.subTest(probes=probe_values):
                with patch.object(mod.urllib.request, "urlopen", side_effect=response):
                    issue = mod.observe("http://prometheus.invalid")
                if expected:
                    self.assertIn(expected, issue)
                else:
                    self.assertEqual(issue, "")

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
        self.assertEqual(message, "", "One healthy observation must not prematurely announce recovery")
        state, message = mod.transition(state, "")
        self.assertIn("rétabli", message)
        state, message = mod.transition(state, "")
        self.assertEqual(message, "")


if __name__ == "__main__":
    unittest.main()
