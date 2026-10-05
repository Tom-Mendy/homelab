#!/usr/bin/env python3
"""Measure NFSv4.1 file-open latency inside a pod with a scratch PVC."""

import argparse
import json
import pathlib
import statistics
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=pathlib.Path)
    parser.add_argument("--max-p95-ms", type=float, default=10)
    args = parser.parse_args()
    root = args.directory.resolve(strict=True)
    mounts = pathlib.Path("/proc/self/mountstats").read_text().split("device ")
    candidates = []
    for mount in mounts:
        line = mount.splitlines()[0] if mount else ""
        if " mounted on " not in line:
            continue
        path = pathlib.Path(line.split(" mounted on ")[1].split(" with fstype ")[0])
        if root == path or path in root.parents:
            candidates.append((len(path.parts), mount))
    mount = max(candidates, key=lambda item: item[0])[1] if candidates else ""
    if " with fstype nfs" not in mount or "vers=4.1," not in mount:
        parser.error("directory must be on an NFSv4.1 mount")

    timings = []
    with tempfile.TemporaryDirectory(prefix="nfs-file-access-", dir=root) as scratch:
        files = [pathlib.Path(scratch) / f"fixture-{i:03d}" for i in range(64)]
        for file in files:
            file.write_bytes(b"x" * 8192)
        started = time.monotonic()
        for _ in range(3):
            for file in files:
                before = time.monotonic()
                with file.open("r+b", buffering=0) as handle:
                    handle.read(8192)
                timings.append((time.monotonic() - before) * 1000)
        elapsed = time.monotonic() - started
    p95 = sorted(timings)[int(len(timings) * 0.95)]
    passed = p95 < args.max_p95_ms
    print(json.dumps({"passed": passed, "operations": len(timings),
                      "total_seconds": round(elapsed, 3),
                      "median_ms": round(statistics.median(timings), 3),
                      "p95_ms": round(p95, 3)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
