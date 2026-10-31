#!/usr/bin/env python3
"""Change-only NFS notifications; scheduler delivers stdout to the home chat.

Two consecutive observations are required. This complements Prometheus rules
without copying a messaging token into the monitoring cluster.
"""
import argparse
import json
import math
import os
import pathlib
import urllib.parse
import urllib.request

DEFAULT_URL = "http://prometheus-server.prometheus.svc.cluster.local"


def transition(previous, issue):
    count = previous.get("failures", 0) + 1 if issue else 0
    alerted = previous.get("alerted", False)
    message = ""
    if issue and count >= 2 and not alerted:
        message = "⚠️ Alerte NFS persistante : " + issue
        alerted = True
    elif not issue and alerted:
        message = "✅ NFS rétabli : les indicateurs surveillés sont revenus sous les seuils d’alerte."
        alerted = False
    return {"failures": count, "alerted": alerted, "issue": issue}, message


def firing_nfs_alerts(alerts):
    return sorted({
        item["labels"].get("node", "cluster") + ": " + item["labels"]["alertname"]
        for item in alerts
        if item.get("state") == "firing" and item.get("labels", {}).get("alertname", "").startswith("NFS")
    })


def observe(url):
    query = 'sum by(node) (rate(node_nfs_requests_total{method="TestStateID"}[5m]))'
    request_url = url.rstrip("/") + "/api/v1/query?" + urllib.parse.urlencode({"query": query})
    try:
        with urllib.request.urlopen(request_url, timeout=20) as response:
            document = json.load(response)
        if document.get("status") != "success":
            return "requête Prometheus en échec"
        samples = {item["metric"]["node"]: float(item["value"][1]) for item in document["data"]["result"]}
        missing = {"node2", "node3"} - set(samples)
        if missing:
            return "métriques NFS absentes : " + ", ".join(sorted(missing))
        failures = [f"{node}: TEST_STATEID={value:.0f}/s" for node, value in sorted(samples.items())
                    if not math.isfinite(value) or value > 100]
        with urllib.request.urlopen(url.rstrip("/") + "/api/v1/alerts", timeout=20) as response:
            alert_document = json.load(response)
        if alert_document.get("status") != "success":
            return "lecture des alertes Prometheus en échec"
        failures.extend(firing_nfs_alerts(alert_document["data"]["alerts"]))
        return "; ".join(failures)
    except Exception as error:
        return "supervision NFS inaccessible (" + type(error).__name__ + ")"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observe-only", action="store_true")
    parser.add_argument("--state", type=pathlib.Path, default=pathlib.Path.home() / "cache/nfs-watchdog-state.json")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    issue = observe(args.url)
    if args.observe_only:
        print(json.dumps({"issue": issue, "healthy": not issue}, ensure_ascii=False))
        return
    try:
        previous = json.loads(args.state.read_text())
    except (FileNotFoundError, ValueError):
        previous = {}
    state, message = transition(previous, issue)
    args.state.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.state.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False))
    os.chmod(temporary, 0o600)
    temporary.replace(args.state)
    if message:
        print(message)


if __name__ == "__main__":
    main()
