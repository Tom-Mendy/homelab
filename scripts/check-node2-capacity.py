#!/usr/bin/env python3
"""Read-only capacity assessment for the documented node2 maintenance profile."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode

GIB = 2 ** 30
MIB = 2 ** 20


def quantity(value):
    match = re.fullmatch(r"([0-9.eE+-]+)([a-zA-Z]*)", str(value))
    if not match:
        raise ValueError("Unsupported Kubernetes quantity")
    multipliers = {"": 1, "n": 1e-9, "u": 1e-6, "m": .001,
                   "k": 1000, "K": 1000, "M": 1e6, "G": 1e9,
                   "T": 1e12, "Ki": 2**10, "Mi": MIB, "Gi": GIB,
                   "Ti": 2**40}
    return float(Decimal(match[1])) * multipliers[match[2]]


def requests(spec):
    """Effective init/sidecar requests, followed by pod-level overrides/overhead."""
    regular = defaultdict(float)
    sidecars = defaultdict(float)
    initialization = defaultdict(float)
    for c in spec.get("containers", []):
        for k, v in c.get("resources", {}).get("requests", {}).items():
            regular[k] += quantity(v)
    for c in spec.get("initContainers", []):
        current = {k: quantity(v) for k, v in
                   c.get("resources", {}).get("requests", {}).items()}
        if c.get("restartPolicy") == "Always":
            for k, v in current.items():
                sidecars[k] += v
            current = dict(sidecars)
        else:
            current = {k: current.get(k, 0) + sidecars[k]
                       for k in current.keys() | sidecars.keys()}
        for k, v in current.items():
            initialization[k] = max(initialization[k], v)
    result = {k: max(regular[k] + sidecars[k], initialization[k])
              for k in regular.keys() | sidecars.keys() | initialization.keys()}
    for k, v in spec.get("resources", {}).get("requests", {}).items():
        result[k] = quantity(v)
    for k, v in spec.get("overhead", {}).items():
        result[k] = result.get(k, 0) + quantity(v)
    return result


def workload(pod):
    for owner in pod["metadata"].get("ownerReferences", []):
        if owner["kind"] == "ReplicaSet":
            return re.sub(r"-[a-z0-9]+$", "", owner["name"])
        if owner["kind"] in {"StatefulSet", "DaemonSet"}:
            return owner["name"]
    return pod["metadata"]["name"]


def paused(pod):
    ns = pod["metadata"]["namespace"]
    name = workload(pod)
    return (ns in {"forgejo-runner", "arc-runners", "coder-workspaces"}
            or ns == "ollama" and name == "ollama"
            or ns == "media" and name in {"qbittorrent", "nzbget"})


def match(expression, values):
    key, op = expression["key"], expression["operator"]
    present = key in values
    expected = expression.get("values", [])
    value = values.get(key)
    if op == "In":
        return present and value in expected
    if op == "NotIn":
        return not present or value not in expected
    if op == "Exists":
        return present
    if op == "DoesNotExist":
        return not present
    if op in {"Gt", "Lt"}:
        return present and len(expected) == 1 and (
            int(value) > int(expected[0]) if op == "Gt"
            else int(value) < int(expected[0]))
    raise ValueError("Unsupported node-affinity operator")


def placement(pod, node):
    spec = pod["spec"]
    labels = node["metadata"]["labels"]
    errors = []
    if any(labels.get(k) != v for k, v in spec.get("nodeSelector", {}).items()):
        errors.append("nodeSelector")
    for taint in node["spec"].get("taints", []):
        if taint["effect"] not in {"NoSchedule", "NoExecute"}:
            continue
        if not any(t.get("effect", taint["effect"]) == taint["effect"] and
                   (not t.get("key") or t["key"] == taint["key"]) and
                   (t.get("operator", "Equal") == "Exists" or
                    t.get("value", "") == taint.get("value", ""))
                   for t in spec.get("tolerations", [])):
            errors.append("taint")
    affinity = spec.get("affinity", {})
    required = affinity.get("nodeAffinity", {}).get(
        "requiredDuringSchedulingIgnoredDuringExecution")
    if required is not None and not any(
        bool(term) and all(match(e, labels) for e in term.get("matchExpressions", []))
        and all(match(e, {"metadata.name": node["metadata"]["name"]})
                for e in term.get("matchFields", []))
        for term in required.get("nodeSelectorTerms", [])
    ):
        errors.append("required node affinity")
    # Fail closed on hard constraints this focused audit does not simulate.
    for kind in ["podAffinity", "podAntiAffinity"]:
        if affinity.get(kind, {}).get("requiredDuringSchedulingIgnoredDuringExecution"):
            errors.append("unmodelled required " + kind)
    if any(t["whenUnsatisfiable"] == "DoNotSchedule"
           for t in spec.get("topologySpreadConstraints", [])):
        errors.append("unmodelled hard topology spread")
    if spec.get("schedulerName", "default-scheduler") != "default-scheduler":
        errors.append("custom scheduler")
    return errors


def capture(root, context):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    base = ["kubectl", "--context", context, "--request-timeout=60s"]

    def save(name, args):
        data = subprocess.run(base + args, check=True, capture_output=True).stdout
        json.loads(data)
        path = root / (name + ".json")
        path.write_bytes(data)
        path.chmod(0o600)

    for name, resource in [("nodes", "nodes"), ("pods", "pods"),
                           ("controllers", "deployments,statefulsets,daemonsets,cronjobs"),
                           ("pv", "pv"), ("pvc", "pvc"), ("pdb", "pdb"),
                           ("hpa", "hpa"), ("services", "services"),
                           ("runners", "autoscalingrunnersets,ephemeralrunnersets,ephemeralrunners")]:
        save(name, ["get", resource, "-A", "-o", "json"])
    for name in ["node2", "node3"]:
        save(name + "-stats", ["get", "--raw", "/api/v1/nodes/" + name + "/proxy/stats/summary"])
    query = 'max by(namespace,pod,container) (max_over_time(container_memory_working_set_bytes{container!="",container!="POD"}[7d]))'
    save("memory-peaks", ["get", "--raw",
         "/api/v1/namespaces/prometheus/services/prometheus-server:80/proxy/api/v1/query?"
         + urlencode({"query": query})])
    (root / "capture.json").write_text(json.dumps({
        "time": datetime.now(timezone.utc).isoformat(), "context": context}) + "\n")


def assess(root):
    def load(name):
        return json.loads((root / (name + ".json")).read_text())

    nodes = {x["metadata"]["name"]: x for x in load("nodes")["items"]}
    node = nodes["node3"]
    pods = [p for p in load("pods")["items"]
            if p["status"]["phase"] not in {"Succeeded", "Failed"}]
    peaks = defaultdict(float)
    metric_data = load("memory-peaks")
    if metric_data.get("status") != "success":
        raise ValueError("Historical memory query failed")
    for x in metric_data["data"]["result"]:
        m = x["metric"]
        key = (m.get("namespace"), m.get("pod"), m.get("container"))
        peaks[key] = max(peaks[key], float(x["value"][1]))
    current = {}
    for name in ["node2", "node3"]:
        for p in load(name + "-stats").get("pods", []):
            for c in p.get("containers", []):
                current[(p["podRef"]["namespace"], p["podRef"]["name"], c["name"])] = c.get("memory", {}).get("workingSetBytes", 0)

    totals = defaultdict(float)
    original = defaultdict(float)
    details, removed, blockers, missing = [], [], [], []
    conditions = {c["type"]: c["status"] for c in node["status"].get("conditions", [])}
    if conditions.get("Ready") != "True" or node["spec"].get("unschedulable"):
        blockers.append("node3 is not Ready and schedulable")
    if any(conditions.get(k) == "True" for k in
           ["MemoryPressure", "DiskPressure", "PIDPressure"]):
        blockers.append("node3 reports resource pressure")
    host_ports = set()
    for pod in pods:
        spec, meta = pod["spec"], pod["metadata"]
        source = spec.get("nodeName")
        if source not in {"node2", "node3"}:
            if source is None:
                blockers.append("Unscheduled pod: " + meta["namespace"] + "/" + meta["name"])
            continue
        req = requests(spec)
        for k, v in req.items():
            original[k] += v
        daemon = any(o["kind"] == "DaemonSet" for o in meta.get("ownerReferences", []))
        mirror = "kubernetes.io/config.mirror" in meta.get("annotations", {})
        if source == "node2" and (daemon or mirror):
            continue
        if paused(pod):
            removed.append({"namespace": meta["namespace"], "workload": workload(pod),
                            "requests_memory_gib": req.get("memory", 0) / GIB})
            continue
        failures = placement(pod, node)
        if failures:
            blockers.append(meta["namespace"] + "/" + meta["name"] + ": " + ", ".join(failures))
        steady = spec["containers"] + [c for c in spec.get("initContainers", [])
                                      if c.get("restartPolicy") == "Always"]
        budget, observed = 0, 0
        for c in steady:
            historical = max((v for (ns, pn, cn), v in peaks.items()
                              if ns == meta["namespace"] and cn == c["name"]
                              and (pn == meta["name"] or
                                   pn.startswith(workload(pod) + "-"))), default=0)
            historical = max(historical, current.get((meta["namespace"], meta["name"], c["name"]), 0))
            requested = quantity(c.get("resources", {}).get("requests", {}).get("memory", 0))
            observed += historical
            budget += max(requested, math.ceil(historical * 1.25 / (64*MIB)) * 64*MIB, 128*MIB)
            if not requested:
                missing.append({"namespace": meta["namespace"], "workload": workload(pod),
                                "container": c["name"], "peak_mib": round(historical/MIB, 1)})
            if not historical:
                blockers.append("No memory sample: " + meta["namespace"] + "/" + meta["name"] + "/" + c["name"])
        budget = max(budget, req.get("memory", 0))
        totals["budget_memory"] += budget
        for k, v in req.items():
            totals[k] += v
        for c in steady:
            for port in c.get("ports", []):
                number = port.get("hostPort", port["containerPort"] if spec.get("hostNetwork") else 0)
                if number:
                    key = (port.get("protocol", "TCP"), number)
                    if key in host_ports:
                        blockers.append("Host port conflict: " + str(key))
                    host_ports.add(key)
        details.append({"namespace": meta["namespace"], "workload": workload(pod),
                        "source": source, "memory_budget_gib": round(budget/GIB, 4),
                        "historical_peak_gib": round(observed/GIB, 4)})

    claims = {(x["metadata"]["namespace"], x["metadata"]["name"]): x
              for x in load("pvc")["items"]}
    volumes = {x["metadata"]["name"]: x for x in load("pv")["items"]}
    for p in pods:
        if p["spec"].get("nodeName") not in {"node2", "node3"} or paused(p):
            continue
        for v in p["spec"].get("volumes", []):
            device = v.get("hostPath") == {"path": "/dev/net/tun", "type": "CharDevice"}
            if "hostPath" in v and not device and not any(o["kind"] == "DaemonSet" for o in p["metadata"].get("ownerReferences", [])) and "kubernetes.io/config.mirror" not in p["metadata"].get("annotations", {}):
                blockers.append("Review application hostPath: " + p["metadata"]["name"])
            if "persistentVolumeClaim" not in v:
                continue
            claim = claims[(p["metadata"]["namespace"], v["persistentVolumeClaim"]["claimName"])]
            pv = volumes[claim["spec"]["volumeName"]]
            if pv["spec"].get("nodeAffinity") or pv["spec"].get("nfs", {}).get("server") != "10.0.0.11":
                blockers.append("Volume is not portable Synology NFS: " + pv["metadata"]["name"])
    if load("hpa")["items"]:
        blockers.append("Review HPA growth before maintenance")
    for controller in load("controllers")["items"]:
        if controller["kind"] in {"Deployment", "StatefulSet"} and controller["spec"].get("replicas", 1) != controller.get("status", {}).get("readyReplicas", 0):
            blockers.append("Controller is not fully Ready: " + controller["metadata"]["name"])
        if controller["kind"] in {"Deployment", "StatefulSet"}:
            pinned = controller["spec"].get("template", {}).get("spec", {}).get("nodeName")
            if pinned and pinned != "node3":
                blockers.append("Controller pins nodeName: " + controller["metadata"]["name"])
    for resource, value in totals.items():
        if resource == "budget_memory":
            continue
        if value > quantity(node["status"]["allocatable"].get(resource, 0)):
            blockers.append("Insufficient " + resource)
    if len(details) > int(node["status"]["allocatable"]["pods"]):
        blockers.append("Pod-count limit exceeded")
    # Explicit planning allowances, not measurements or Kubernetes reservations.
    system_allowance, operational_margin = 2*GIB, 4*GIB
    required = totals["budget_memory"] + system_allowance + operational_margin
    available = quantity(node["status"]["allocatable"]["memory"])
    if required > available:
        blockers.append("Insufficient conservative memory headroom")
    result = {
        "scope": "Static assessment; not a scheduler replay or a live evacuation test",
        "profile_passed": not blockers, "blockers": sorted(set(blockers)),
        "node3_allocatable_gib": round(available/GIB, 3),
        "original_worker_requests_gib": round(original["memory"]/GIB, 3),
        "profile_requests_gib": round(totals["memory"]/GIB, 3),
        "profile_cpu_requests": round(totals["cpu"], 3),
        "profile_memory_budget_gib": round(totals["budget_memory"]/GIB, 3),
        "system_allowance_gib": 2, "operational_margin_gib": 4,
        "remaining_after_allowances_gib": round((available-required)/GIB, 3),
        "profile_pods": len(details), "paused_workloads": removed,
        "workload_budgets": details, "missing_memory_requests": missing,
        "pdbs_requiring_separate_eviction_plan": [
            x["metadata"]["namespace"] + "/" + x["metadata"]["name"]
            for x in load("pdb")["items"] if not x.get("status", {}).get("disruptionsAllowed", 0)],
        "window_ready": False,
        "window_note": "Capacity assessment never authorizes evacuation; apply and verify the runbook gates first.",
        "conditions": ["CI intake disabled and jobs drained", "All documented pause targets stopped",
                       "Scheduled jobs serialized or temporarily suspended",
                       "No inference, bulk downloads, or workspace restarts during maintenance",
                       "Re-run capture immediately before evacuation and observe after relocation"],
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--context", default="kubernetes-admin@cluster.local")
    args = parser.parse_args()
    if args.capture:
        capture(args.evidence, args.context)
    result = assess(args.evidence)
    path = args.evidence / "capacity-result.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    path.chmod(0o600)
    print(json.dumps({k: v for k, v in result.items() if k not in {
        "workload_budgets", "missing_memory_requests", "paused_workloads"}}, indent=2))
    raise SystemExit(0 if result["profile_passed"] else 1)


if __name__ == "__main__":
    main()
