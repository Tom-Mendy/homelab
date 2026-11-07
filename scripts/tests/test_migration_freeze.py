"""Protect existing incident holds and prevent partial thaw on identity drift."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "migration_freeze", Path(__file__).parents[1] / "migration-version-freeze.py")
FREEZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FREEZE)


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.entries = [
            {"resource": "imageupdateautomations", "namespace": "flux-system",
             "name": "incident-held", "uid": "first", "suspend": True, "guard": None},
            {"resource": "imageupdateautomations", "namespace": "flux-system",
             "name": "normal", "uid": "second", "suspend": None, "guard": None},
        ]
        FREEZE.write(self.root / "resume-state.json", {
            "context": "test-cluster", "objects": self.entries})

    def live(self, context, args):
        entry = next(e for e in self.entries if e["name"] == args[2])
        return {"metadata": {"uid": entry["uid"], "annotations": {FREEZE.GUARD: "disabled"}},
                "spec": {"suspend": True}}

    def test_thaw_preserves_the_preexisting_incident_hold(self):
        with patch.object(FREEZE, "kube", side_effect=self.live), \
                patch.object(FREEZE, "protected_patch") as mutate:
            FREEZE.restore("test-cluster", self.root)
        first, second = mutate.call_args_list[:2]
        self.assertEqual(first.args[2]["spec"], {"suspend": True})
        self.assertEqual(second.args[2]["spec"], {"suspend": None})
        self.assertIsNone(mutate.call_args_list[-1].args[2]["metadata"]["annotations"][FREEZE.GUARD])

    def test_replaced_second_resource_prevents_any_partial_thaw(self):
        def replaced(context, args):
            obj = self.live(context, args)
            if args[2] == "normal":
                obj["metadata"]["uid"] = "replacement"
            return obj

        with patch.object(FREEZE, "kube", side_effect=replaced), \
                patch.object(FREEZE, "protected_patch") as mutate:
            with self.assertRaises(ValueError):
                FREEZE.restore("test-cluster", self.root)
        mutate.assert_not_called()

    def test_another_clusters_resume_file_cannot_be_used(self):
        with patch.object(FREEZE, "kube") as read, \
                patch.object(FREEZE, "protected_patch") as mutate:
            with self.assertRaises(ValueError):
                FREEZE.restore("different-cluster", self.root)
        read.assert_not_called()
        mutate.assert_not_called()

    def test_refreeze_does_not_replace_the_recorded_baseline(self):
        FREEZE.write(self.root / "baseline.json", {"workload_images": {"app": "old@sha256:abc"}})
        before = (self.root / "baseline.json").read_bytes()
        with patch.object(FREEZE, "protected_patch"), \
                patch.object(FREEZE, "baseline", return_value={"app": "new"}) as capture:
            FREEZE.suspend("test-cluster", self.root)
        self.assertEqual(before, (self.root / "baseline.json").read_bytes())
        capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
