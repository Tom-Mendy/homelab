#!/usr/bin/env python3
"""Recover one NFS client from an independent Kubernetes maintenance Job.

The Job waits for an explicit ConfigMap approval, moves Hermes first, deletes
managed application pods gracefully (planned single-instance PDB bypass), and
only reboots after every non-DaemonSet application pod has disappeared. It never
force-deletes pods, changes storage, prints tokens, or changes NAS settings.
"""
import json
import os
import pathlib
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

NAMESPACE = "nfs-maintenance"
CONTROL = "nfs-worker-recovery"
IMAGE = "docker.io/library/python@sha256:8acac70227ce3b34da9453120c375cc5b66cd0b062d4dc6bc74286f81a3819e1"


def drain_candidate(pod):
    metadata = pod["metadata"]
    if "kubernetes.io/config.mirror" in metadata.get("annotations", {}):
        return False
    owners = metadata.get("ownerReferences", [])
    if any(owner["kind"] == "DaemonSet" for owner in owners):
        return False
    if not owners:
        raise ValueError("Refusing to delete unmanaged pod: " + metadata.get("name", "unknown"))
    return True


class API:
    def __init__(self):
        root = pathlib.Path("/var/run/secrets/kubernetes.io/serviceaccount")
        self.root = root
        self.context = ssl.create_default_context(cafile=str(root / "ca.crt"))
        self.base = "https://kubernetes.default.svc"

    def call(self, path, method="GET", body=None):
        data = None if body is None else json.dumps(body).encode()
        for attempt in range(4):
            request = urllib.request.Request(self.base + path, data=data, method=method, headers={
                "Authorization": "Bearer " + (self.root / "token").read_text().strip(),
                "Content-Type": "application/merge-patch+json" if method == "PATCH" else "application/json",
            })
            try:
                with urllib.request.urlopen(request, context=self.context, timeout=35) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise
                time.sleep(2 ** attempt)
            except (TimeoutError, urllib.error.URLError):
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)

    def pods(self, node):
        query = urllib.parse.urlencode({"fieldSelector": "spec.nodeName=" + node})
        return self.call("/api/v1/pods?" + query)["items"]

    def status(self, stage, **details):
        print(json.dumps({"stage": stage, **details}), flush=True)
        self.call(f"/api/v1/namespaces/{NAMESPACE}/configmaps/{CONTROL}", "PATCH", {
            "data": {"stage": stage, "details": json.dumps(details), "updated_unix": str(time.time())}})


def wait_for(check, seconds, label):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        result = check()
        if result:
            return result
        time.sleep(5)
    raise TimeoutError(label)


def ready(pod):
    return not pod["metadata"].get("deletionTimestamp") and any(
        condition["type"] == "Ready" and condition["status"] == "True"
        for condition in pod.get("status", {}).get("conditions", []))


def delete_and_wait(api, pod):
    metadata = pod["metadata"]
    path = f"/api/v1/namespaces/{metadata['namespace']}/pods/{metadata['name']}"
    print(json.dumps({"graceful_delete": metadata["namespace"] + "/" + metadata["name"]}), flush=True)
    try:
        api.call(path, "DELETE", {"apiVersion": "v1", "kind": "DeleteOptions",
                                 "preconditions": {"uid": metadata["uid"]}})
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    def gone():
        try:
            current = api.call(path)
            return current["metadata"]["uid"] != metadata["uid"]
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return True
            raise
    wait_for(gone, 1900, "Pod did not terminate cleanly: " + path)


def stateid_count(ip):
    with urllib.request.urlopen("http://" + ip + ":9100/metrics", timeout=20) as response:
        text = response.read().decode()
    return sum(float(line.rsplit(" ", 1)[1]) for line in text.splitlines()
               if line.startswith("node_nfs_requests_total{") and 'method="TestStateID"' in line)


def main():
    api = API()
    worker = os.environ.get("RECOVERY_WORKER", "node3")
    controller = os.environ["CONTROLLER_NODE"]
    if worker == controller:
        raise ValueError("Recovery must run on a different node")
    node = api.call("/api/v1/nodes/" + worker)
    if node["spec"].get("unschedulable"):
        raise ValueError("Worker was already cordoned; refusing to alter its maintenance state")
    candidates = [pod for pod in api.pods(worker) if drain_candidate(pod)]
    original_boot = node["status"]["nodeInfo"]["bootID"]
    baseline = []
    for resource in ("deployments", "statefulsets"):
        for obj in api.call("/apis/apps/v1/" + resource)["items"]:
            desired = obj["spec"].get("replicas", 1)
            if desired > 0 and obj.get("status", {}).get("readyReplicas", 0) >= desired:
                baseline.append((resource, obj["metadata"]["namespace"], obj["metadata"]["name"], desired))
    api.status("Prepared", worker=worker, controller=controller, boot_id=original_boot,
               pods=len(candidates), healthy_controllers=len(baseline))
    def approved():
        cm = api.call(f"/api/v1/namespaces/{NAMESPACE}/configmaps/{CONTROL}")
        return cm["data"].get("execute") == "true"
    wait_for(approved, 3600, "Approval was not provided")
    cordoned = False
    reboot_requested = False
    try:
        api.call("/api/v1/nodes/" + worker, "PATCH", {"spec": {"unschedulable": True}})
        cordoned = True
        api.status("MovingHermes", worker=worker)
        hermes = [pod for pod in api.pods(worker)
                  if pod["metadata"].get("labels", {}).get("app.kubernetes.io/name") == "hermes-workspace"]
        if len(hermes) != 1:
            raise ValueError("Expected exactly one Hermes workspace to relocate")
        delete_and_wait(api, hermes[0])
        wait_for(lambda: any(pod["metadata"].get("labels", {}).get("app.kubernetes.io/name") == "hermes-workspace"
                             and ready(pod) for pod in api.pods(controller)), 600, "Hermes did not recover on controller node")
        api.status("Draining", worker=worker)
        candidates = [pod for pod in api.pods(worker) if drain_candidate(pod)]
        # Preserve each pod's configured grace period. No eviction/force-delete.
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda pod: delete_and_wait(api, pod), candidates))
        remaining = [pod for pod in api.pods(worker) if drain_candidate(pod)]
        if remaining:
            raise RuntimeError("Application pods remain; refusing to reboot")
        api.status("Rebooting", worker=worker, boot_id=original_boot)
        reboot = {"apiVersion": "v1", "kind": "Pod", "metadata": {
            "name": "nfs-worker-reboot", "namespace": NAMESPACE,
            "labels": {"app.kubernetes.io/name": "nfs-worker-recovery"}}, "spec": {
            "nodeName": worker, "hostPID": True, "restartPolicy": "Never",
            "automountServiceAccountToken": False,
            "containers": [{"name": "reboot", "image": IMAGE, "imagePullPolicy": "IfNotPresent",
                "command": ["python3", "-c", "import subprocess,time; time.sleep(5); subprocess.run(['/usr/sbin/chroot','/host','/usr/bin/systemctl','reboot'],check=True)"],
                "securityContext": {"privileged": True, "runAsUser": 0},
                "resources": {"requests": {"cpu": "10m", "memory": "32Mi"}, "limits": {"memory": "128Mi"}},
                "volumeMounts": [{"name": "host", "mountPath": "/host", "readOnly": True}]}],
            "volumes": [{"name": "host", "hostPath": {"path": "/", "type": "Directory"}}]}}
        api.call(f"/api/v1/namespaces/{NAMESPACE}/pods", "POST", reboot)
        reboot_requested = True
        def rebooted_ready():
            current = api.call("/api/v1/nodes/" + worker)
            return current["status"]["nodeInfo"]["bootID"] != original_boot and any(
                condition["type"] == "Ready" and condition["status"] == "True"
                for condition in current["status"]["conditions"])
        wait_for(rebooted_ready, 900, "Worker did not return Ready with a new boot ID")
        api.call("/api/v1/nodes/" + worker, "PATCH", {"spec": {"unschedulable": False}})
        cordoned = False
        api.status("Restoring", worker=worker)
        def recovered():
            for resource, namespace, name, desired in baseline:
                obj = api.call(f"/apis/apps/v1/namespaces/{namespace}/{resource}/{name}")
                if obj.get("status", {}).get("readyReplicas", 0) < desired:
                    return False
            return True
        wait_for(recovered, 1500, "Previously healthy controllers did not recover")
        node = api.call("/api/v1/nodes/" + worker)
        ip = next(address["address"] for address in node["status"]["addresses"] if address["type"] == "InternalIP")
        first = stateid_count(ip)
        started = time.monotonic()
        time.sleep(20)
        rate = (stateid_count(ip) - first) / (time.monotonic() - started)
        if rate >= 100:
            raise RuntimeError("NFS TEST_STATEID storm persists after reboot")
        api.status("Succeeded", worker=worker, boot_id=node["status"]["nodeInfo"]["bootID"],
                   test_stateid_per_second=round(rate, 3), recovered_controllers=len(baseline))
    except Exception as error:
        # A failed drain must not strand workloads. After a failed reboot, keep
        # the worker cordoned until an administrator checks its actual state.
        if cordoned and not reboot_requested:
            api.call("/api/v1/nodes/" + worker, "PATCH", {"spec": {"unschedulable": False}})
        api.status("Failed", error=type(error).__name__, message=str(error)[:500], reboot_requested=reboot_requested)
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Recovery stopped: " + type(error).__name__, file=sys.stderr, flush=True)
        sys.exit(1)
