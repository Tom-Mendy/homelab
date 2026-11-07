#!/usr/bin/env python3
"""Suspend Flux image writers/scanners, preserve prior holds, and check drift."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

GUARD = "kustomize.toolkit.fluxcd.io/reconcile"
RESOURCES = ["imageupdateautomations", "imagerepositories"]


def kube(context, args):
    process = subprocess.run(["kubectl", "--context", context, "--request-timeout=45s"]
                             + args, capture_output=True, check=True)
    return json.loads(process.stdout) if process.stdout else None


def items(context, resource):
    return kube(context, ["get", resource, "-A", "-o", "json"])["items"]


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def protected_patch(context, entry, changes):
    for attempt in range(5):
        current = kube(context, ["get", entry["resource"], entry["name"], "-n",
                                 entry["namespace"], "-o", "json"])
        if current["metadata"]["uid"] != entry["uid"]:
            raise ValueError("Automation was replaced; inspect its saved state")
        changes.setdefault("metadata", {})["resourceVersion"] = current["metadata"]["resourceVersion"]
        try:
            return kube(context, ["patch", entry["resource"], entry["name"], "-n",
                                  entry["namespace"], "--type=merge", "-p",
                                  json.dumps(changes), "-o", "json"])
        except subprocess.CalledProcessError as error:
            if attempt == 4 or not any(x in error.stderr for x in [b"Conflict", b"object has been modified"]):
                raise


def baseline(context):
    images = {}
    for obj in items(context, "deployments,statefulsets,daemonsets,cronjobs"):
        spec = obj["spec"]
        if obj["kind"] == "CronJob":
            spec = spec["jobTemplate"]["spec"]
        pod = spec["template"]["spec"]
        key = "/".join([obj["kind"], obj["metadata"]["namespace"], obj["metadata"]["name"]])
        images[key] = {group + "/" + c["name"]: c["image"]
                       for group in ["containers", "initContainers"]
                       for c in pod.get(group, [])}
    runtime = {}
    for pod in items(context, "pods"):
        if pod["status"]["phase"] in {"Succeeded", "Failed"}:
            continue
        for group in ["containerStatuses", "initContainerStatuses"]:
            for c in pod["status"].get(group, []):
                if c.get("imageID"):
                    key = pod["metadata"]["namespace"] + "/" + c["name"] + "/" + c["image"]
                    runtime.setdefault(key, set()).add(c["imageID"])
    return {
        "workload_images": images,
        "runtime_image_ids": {k: sorted(v) for k, v in runtime.items()},
        "git_revisions": {o["metadata"]["name"]: o.get("status", {}).get("artifact", {}).get("revision")
                          for o in items(context, "gitrepositories")},
        "helm_chart_selections": {o["metadata"]["name"]: {
            "chart": o["spec"].get("chart"), "chartRef": o["spec"].get("chartRef"),
            "lastAppliedRevision": o.get("status", {}).get("lastAppliedRevision")}
            for o in items(context, "helmreleases")},
    }


def suspend(context, root):
    path = root / "resume-state.json"
    if not path.exists():
        saved = []
        for resource in RESOURCES:
            for obj in items(context, resource):
                saved.append({"resource": resource, "namespace": obj["metadata"]["namespace"],
                              "name": obj["metadata"]["name"], "uid": obj["metadata"]["uid"],
                              "suspend": obj["spec"].get("suspend"),
                              "guard": obj["metadata"].get("annotations", {}).get(GUARD)})
        write(path, {"context": context, "captured_at": datetime.now(timezone.utc).isoformat(),
                     "objects": saved})
        write(root / "baseline-before.json", baseline(context))
    state = json.loads(path.read_text())
    if state["context"] != context:
        raise ValueError("Resume state belongs to a different context")
    for entry in state["objects"]:
        protected_patch(context, entry, {"metadata": {"annotations": {GUARD: "disabled"}},
                                         "spec": {"suspend": True}})
    # Keep a fixed baseline: re-running freeze must never bless newer images.
    if not (root / "baseline.json").exists():
        write(root / "baseline.json", json.loads((root / "baseline-before.json").read_text()))


def restore(context, root):
    state = json.loads((root / "resume-state.json").read_text())
    if state["context"] != context:
        raise ValueError("Resume state belongs to a different context")
    # Validate every identity before resuming any writer.
    for entry in state["objects"]:
        current = kube(context, ["get", entry["resource"], entry["name"], "-n",
                                 entry["namespace"], "-o", "json"])
        if current["metadata"]["uid"] != entry["uid"]:
            raise ValueError("Automation was replaced; manual review required")
        if not current["spec"].get("suspend") or current["metadata"].get("annotations", {}).get(GUARD) != "disabled":
            raise ValueError("Freeze was changed by another actor; inspect before thaw")
    # Restore suspension flags before removing their Git reconciliation guards.
    for entry in state["objects"]:
        protected_patch(context, entry, {"spec": {"suspend": entry["suspend"]}})
    for entry in state["objects"]:
        protected_patch(context, entry, {"metadata": {"annotations": {GUARD: entry["guard"]}}})
    write(root / "restored.json", {"time": datetime.now(timezone.utc).isoformat(),
                                   "original_holds_preserved": True})


def check(context, root, strict):
    problems = []
    objects = []
    for resource in RESOURCES:
        for obj in items(context, resource):
            name = resource + "/" + obj["metadata"]["namespace"] + "/" + obj["metadata"]["name"]
            objects.append(name)
            if not obj["spec"].get("suspend") or obj["metadata"].get("annotations", {}).get(GUARD) != "disabled":
                problems.append("Image update freeze not protected: " + name)
            if any(c["type"] == "Reconciling" and c["status"] == "True"
                   for c in obj.get("status", {}).get("conditions", [])):
                problems.append("Image reconciliation is still in flight: " + name)
    expected = json.loads((root / "resume-state.json").read_text())
    if expected["context"] != context:
        raise ValueError("Resume state belongs to a different context")
    if len(objects) != len(expected["objects"]) or not objects:
        problems.append("Image automation inventory changed")
    now = baseline(context)
    old = json.loads((root / "baseline.json").read_text())
    drift = [key for key in old if old[key] != now[key]]
    if strict and drift:
        problems.append("Baseline drift: " + ", ".join(drift))
    for obj in items(context, "fluxinstances"):
        version = obj["spec"]["distribution"]["version"]
        if not re.fullmatch(r"v?\d+\.\d+\.\d+", version):
            problems.append("Flux distribution still has a floating version")
    result = {"image_automation_frozen": not problems, "problems": problems,
              "objects": objects, "baseline_drift": drift,
              "strict_baseline": strict, "maintenance_window_ready": False,
              "note": "CI drain, publisher controls and mutable-image checks remain window gates."}
    write(root / "freeze-check.json", result)
    return result


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "check", "restore"])
    parser.add_argument("--context", default="kubernetes-admin@cluster.local")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--strict-baseline", action="store_true")
    args = parser.parse_args()
    args.state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if args.action == "freeze":
        suspend(args.context, args.state)
    elif args.action == "restore":
        restore(args.context, args.state)
        print("Original image automation states restored; verify Git desired state too.")
        return
    result = check(args.context, args.state, args.strict_baseline)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["image_automation_frozen"] else 1)


if __name__ == "__main__":
    main()
