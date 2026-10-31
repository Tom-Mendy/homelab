#!/usr/bin/env python3
"""Offline validation of the exact upstream rules and local extras chart."""
import argparse
from pathlib import Path
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[3]
CHART = ROOT / "kubernetes/prometheus"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-chart", required=True, help="Downloaded prometheus 29.36.1 chart archive")
    parser.add_argument("--promtool", default="promtool")
    args = parser.parse_args()
    subprocess.run(["helm", "lint", str(CHART)], check=True)
    subprocess.run(["helm", "lint", args.upstream_chart, "-f", str(CHART / "values.yaml")], check=True)
    upstream = subprocess.check_output([
        "helm", "template", "prometheus", args.upstream_chart, "-n", "prometheus",
        "-f", str(CHART / "values.yaml"),
    ], text=True)
    documents = list(yaml.safe_load_all(upstream))
    config = next(doc["data"] for doc in documents if doc and doc["kind"] == "ConfigMap"
                  and "prometheus.yml" in doc.get("data", {}))
    prometheus = yaml.safe_load(config["prometheus.yml"])
    assert "/etc/config/alerting_rules.yml" in prometheus["rule_files"]
    assert "alerting" not in prometheus, "Do not enable an unconfigured notification receiver"
    job = next(job for job in prometheus["scrape_configs"] if job["job_name"] == "nfs-worker-probe")
    assert job["scrape_timeout"] == "5s"
    extras = subprocess.check_output(["helm", "template", "prometheus-extras", str(CHART)], text=True)
    extra_docs = [doc for doc in yaml.safe_load_all(extras) if doc]
    script = next(doc["data"]["nfs-probe.py"] for doc in extra_docs
                  if doc["kind"] == "ConfigMap" and doc["metadata"]["name"] == "nfs-worker-probe")
    assert script == (CHART / "files/nfs-probe.py").read_text()
    with tempfile.TemporaryDirectory(prefix="nfs-rules-check-") as directory:
        work = Path(directory)
        rule_file = work / "nfs-alerting-rules.yml"
        rule_file.write_text(config["alerting_rules.yml"])
        tests = yaml.safe_load((CHART / "tests/nfs-rules.test.yaml").read_text())
        tests["rule_files"] = [str(rule_file)]
        test_file = work / "nfs-rules.test.yaml"
        test_file.write_text(yaml.safe_dump(tests))
        subprocess.run([args.promtool, "check", "rules", str(rule_file)], check=True)
        subprocess.run([args.promtool, "test", "rules", str(test_file)], check=True)
    print("Rendered upstream rule loading, dedicated scrape, extras script, and 7 PromQL scenarios: OK")


if __name__ == "__main__":
    main()
