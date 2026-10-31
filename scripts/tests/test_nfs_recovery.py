"""Safety gates for the independent worker recovery controller."""
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "recover-nfs-worker.py"


class RecoveryTests(unittest.TestCase):
    def test_drain_excludes_daemonsets_and_static_pods(self):
        self.assertTrue(PATH.is_file(), "recovery controller is missing")
        spec = importlib.util.spec_from_file_location("recovery", PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        daemon = {"metadata": {"ownerReferences": [{"kind": "DaemonSet"}]}}
        mirror = {"metadata": {"annotations": {"kubernetes.io/config.mirror": "hash"}}}
        deployment = {"metadata": {"ownerReferences": [{"kind": "ReplicaSet"}]}}
        orphan = {"metadata": {"name": "unmanaged"}}
        self.assertFalse(module.drain_candidate(daemon))
        self.assertFalse(module.drain_candidate(mirror))
        self.assertTrue(module.drain_candidate(deployment))
        with self.assertRaises(ValueError):
            module.drain_candidate(orphan)


if __name__ == "__main__":
    unittest.main()
