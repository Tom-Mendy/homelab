"""Offline NFS probe tests; never access an application volume or cluster."""
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "kubernetes/prometheus/files/nfs-probe.py"


def load_probe():
    spec = importlib.util.spec_from_file_location("nfs_probe", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BatchTests(unittest.TestCase):
    def test_probe_source_exists(self):
        self.assertTrue(SOURCE.is_file(), "The isolated NFS probe is not implemented")

    def test_nearest_rank_and_reject_incomplete_or_invalid_samples(self):
        probe = load_probe()
        self.assertEqual(probe.percentile95(list(range(96)), 96), 91)
        for samples in ([1], [float("nan")] * 96, [-1] * 96, [math.inf] * 96):
            with self.assertRaises(ValueError):
                probe.percentile95(samples, 96)

    def test_fixtures_are_small_validated_and_not_rewritten(self):
        probe = load_probe()
        with tempfile.TemporaryDirectory(prefix="nfs-probe-test-") as directory:
            root = Path(directory)
            first = probe.measure(root, "node2", "pod-a")
            self.assertEqual(first["samples"], 96)
            files = sorted((root / "node2-pod-a").iterdir())
            self.assertEqual(len(files), 32)
            self.assertEqual(sum(p.stat().st_size for p in files), 131072)
            original = [p.stat().st_mtime_ns for p in files]
            self.assertEqual(probe.measure(root, "node2", "pod-a")["samples"], 96)
            self.assertEqual(original, [p.stat().st_mtime_ns for p in files])
            probe.measure(root, "node3", "pod-b")
            self.assertTrue((root / "node3-pod-b").is_dir())
            for invalid in (b"x", b"x" * 4096, probe.PAYLOAD + b"extra"):
                files[0].write_bytes(invalid)
                with self.assertRaises(ValueError):
                    probe.measure(root, "node2", "pod-a")
            with self.assertRaises(ValueError):
                probe.measure(root, "../outside", "pod-a")

    def test_mount_validation_uses_deepest_mount_and_exact_options(self):
        probe = load_probe()
        mountinfo = (
            "1 0 0:1 / / rw - overlay overlay rw\n"
            "2 1 0:2 / /scratch rw - nfs4 nas:/volume1/k8s rw,vers=4.1\n"
            "3 2 0:3 / /scratch/local rw - tmpfs tmpfs rw\n"
            "4 1 0:4 / /space\\040name rw - nfs nas:/x rw,opts:vers=4.1\n"
        )
        probe.validate_mount("/scratch", mountinfo)
        probe.validate_mount("/space name/data", mountinfo)
        for path in ("/scratch/local/x", "/scratch-other"):
            with self.assertRaises(ValueError):
                probe.validate_mount(path, mountinfo)
        with self.assertRaises(ValueError):
            probe.validate_mount("/scratch", mountinfo.replace("vers=4.1", "vers=4.10"))


class SupervisorTests(unittest.TestCase):
    def test_real_exporter_reports_mount_failure_without_blocking_http(self):
        import socket
        import subprocess
        import sys
        import time
        import urllib.error
        import urllib.request
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        process = subprocess.Popen(
            [sys.executable, "-B", str(SOURCE), "--port", str(port),
             "--root", "/not-a-real-nfs-mount"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=1) as response:
                        metrics = response.read().decode()
                    stamp = next(line.split()[1] for line in metrics.splitlines()
                                 if line.startswith("nfs_probe_last_result_timestamp_seconds "))
                    if float(stamp) > 0:
                        break
                except (urllib.error.URLError, StopIteration):
                    pass
                time.sleep(0.05)
            else:
                self.fail("Real exporter did not report its bounded child failure")
            self.assertIn("nfs_probe_success 0\n", metrics)
            self.assertNotIn("nfs_probe_p95_seconds", metrics)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1) as response:
                self.assertEqual(response.status, 200)
        finally:
            process.terminate()
            process.wait(timeout=3)
            if process.stderr is not None:
                process.stderr.close()

    def test_timeout_never_waits_or_accumulates_blocked_children(self):
        probe = load_probe()

        class Blocked:
            returncode = None
            killed = 0
            def poll(self):
                return self.returncode
            def kill(self):
                self.killed += 1
            def wait(self, *args, **kwargs):
                raise AssertionError("Must never wait for blocked NFS")

        child = Blocked()
        spawned = []
        def spawn():
            spawned.append(child)
            return child

        supervisor = probe.Supervisor(spawn, interval=60, timeout=20)
        supervisor.tick(0, 100)
        supervisor.tick(21, 121)
        for now in range(22, 500):
            supervisor.tick(now, 100 + now)
        self.assertEqual(len(spawned), 1)
        self.assertEqual(child.killed, 1)
        self.assertIn("nfs_probe_timeouts_total 1\n", supervisor.metrics())
        self.assertIn("nfs_probe_success 0\n", supervisor.metrics())
        self.assertIn("nfs_probe_last_result_timestamp_seconds 121\n", supervisor.metrics())
        self.assertNotIn("nfs_probe_p95_seconds", supervisor.metrics())
        # Exporter HTTP remains live even while the child ignores SIGKILL.
        import threading
        import urllib.request
        server = probe.make_server(supervisor, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}"
            with urllib.request.urlopen(base + "/metrics", timeout=1) as response:
                self.assertIn(b"nfs_probe_child_blocked 1", response.read())
            with urllib.request.urlopen(base + "/healthz", timeout=1) as response:
                self.assertEqual(response.status, 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_success_failure_and_late_result_are_not_fresh_success(self):
        import io
        import json
        probe = load_probe()

        class Completed:
            def __init__(self, result, code=0):
                self.returncode = code
                self.stdout = io.BytesIO(json.dumps(result).encode())
            def poll(self):
                return self.returncode

        valid = {"samples": 96, "p95_seconds": 0.001}
        for invalid in ({"samples": 95, "p95_seconds": 0.001},
                        {"samples": 96, "p95_seconds": -1},
                        {"samples": 96, "p95_seconds": math.nan}):
            children = iter([Completed(valid), Completed(invalid)])
            supervisor = probe.Supervisor(lambda: next(children), interval=60, timeout=20)
            supervisor.tick(0, 100)
            supervisor.tick(1, 101)
            self.assertIn("nfs_probe_success 1\n", supervisor.metrics())
            supervisor.tick(60, 160)
            supervisor.tick(61, 161)
            metrics = supervisor.metrics()
            self.assertIn("nfs_probe_success 0\n", metrics)
            self.assertIn("nfs_probe_last_success_timestamp_seconds 101\n", metrics)
            self.assertNotIn("nfs_probe_p95_seconds", metrics)
        late = Completed(valid)
        supervisor = probe.Supervisor(lambda: late, interval=60, timeout=20)
        supervisor.tick(0, 100)
        supervisor.timed_out = True
        supervisor.tick(22, 122)
        self.assertNotIn("nfs_probe_success 1\n", supervisor.metrics())


class ManifestTests(unittest.TestCase):
    def test_worker_chart_and_loaded_rules(self):
        import subprocess
        import yaml
        values = yaml.safe_load((ROOT / "kubernetes/prometheus/values.yaml").read_text())
        self.assertIn("serverFiles", values, "Standalone Prometheus rules must be loaded via serverFiles")
        rules = values["serverFiles"]["alerting_rules.yml"]["groups"]
        names = {rule.get("alert") for group in rules for rule in group["rules"]}
        self.assertTrue({"NFSTestStateIDStorm", "NFSProbeSlow", "NFSProbeFailed", "NFSProbeStale",
                         "NFSProbeScrapeMissing", "NFSProbeCoverageMissing", "NFSClientMetricsMissing"} <= names)
        rendered = subprocess.check_output(["helm", "template", "prometheus-extras", "kubernetes/prometheus"], cwd=ROOT, text=True)
        documents = [doc for doc in yaml.safe_load_all(rendered) if doc]
        ds = next(doc for doc in documents if doc["kind"] == "DaemonSet")
        pod = ds["spec"]["template"]["spec"]
        self.assertFalse(pod["automountServiceAccountToken"])
        self.assertEqual(pod["nodeSelector"], {"kubernetes.io/os": "linux"})
        terms = pod["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]["nodeSelectorTerms"]
        self.assertTrue(all({"key": "node-role.kubernetes.io/control-plane", "operator": "DoesNotExist"}
                            in term["matchExpressions"] for term in terms))
        self.assertEqual(pod["securityContext"]["seccompProfile"]["type"], "RuntimeDefault")
        self.assertTrue(pod["securityContext"]["runAsNonRoot"])
        self.assertNotIn("initContainers", pod)
        container = pod["containers"][0]
        self.assertEqual(container["image"], "docker.io/library/python@sha256:8acac70227ce3b34da9453120c375cc5b66cd0b062d4dc6bc74286f81a3819e1")
        self.assertTrue(container["securityContext"]["readOnlyRootFilesystem"])
        self.assertFalse(container["securityContext"]["allowPrivilegeEscalation"])
        self.assertEqual(container["securityContext"]["capabilities"]["drop"], ["ALL"])
        self.assertTrue(all("hostPath" not in volume for volume in pod["volumes"]))
        claim = next(doc for doc in documents if doc["kind"] == "PersistentVolumeClaim" and doc["metadata"]["name"] == "nfs-probe-scratch")
        self.assertEqual(claim["spec"]["storageClassName"], "nfs-k8s")
        self.assertEqual(claim["spec"]["accessModes"], ["ReadWriteMany"])
        jobs = yaml.safe_load(values["extraScrapeConfigs"])
        self.assertEqual(jobs[0]["job_name"], "nfs-worker-probe")
        self.assertTrue(any(rule.get("target_label") == "node" for rule in jobs[0]["relabel_configs"]))
        self.assertFalse(values["alertmanager"]["enabled"])


if __name__ == "__main__":
    unittest.main()
