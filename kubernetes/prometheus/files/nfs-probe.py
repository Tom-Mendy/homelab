#!/usr/bin/env python3
"""Low-impact scratch-only NFSv4.1 probe; HTTP never touches the mount."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import subprocess
import sys
import threading
from pathlib import Path
import re
import time

PAYLOAD = bytes(range(256)) * 16
FIXTURES = 32
PASSES = 3


def percentile95(samples, expected):
    if len(samples) != expected or not samples or any(
        not math.isfinite(value) or value < 0 for value in samples
    ):
        raise ValueError("Incomplete or invalid latency samples")
    return sorted(samples)[math.ceil(0.95 * len(samples)) - 1]


def validate_mount(path, mountinfo):
    """Parse mountinfo without resolving/statting a potentially blocked path."""
    matches = []
    for line in mountinfo.splitlines():
        left, right = line.split(" - ", 1)
        fields, source = left.split(), right.split()
        mount = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), fields[4])
        if path == mount or path.startswith(mount.rstrip("/") + "/"):
            options = {token.removeprefix("opts:") for token in (fields[5] + "," + source[2]).split(",")}
            matches.append((len(mount), source[0], options))
    if not matches:
        raise ValueError("Scratch mount not found")
    _, kind, options = max(matches, key=lambda match: match[0])
    if kind not in ("nfs", "nfs4") or "vers=4.1" not in options:
        raise ValueError("Scratch must be an NFSv4.1 mount")


def measure(root, node, uid):
    for identifier in (node, uid):
        if not re.fullmatch(r"[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,252}", identifier):
            raise ValueError("Invalid scratch identifier")
    directory = Path(root) / (node + "-" + uid)
    directory.mkdir(mode=0o700, exist_ok=True)
    fixtures = [directory / f"fixture-{index:02d}" for index in range(FIXTURES)]
    for path in fixtures:
        try:
            with path.open("xb", buffering=0) as stream:
                if stream.write(PAYLOAD) != len(PAYLOAD):
                    raise ValueError("Incomplete fixture initialization")
        except FileExistsError:
            pass
    samples = []
    for _ in range(PASSES):
        for path in fixtures:
            started = time.monotonic()
            # Writable OPEN exercises NFSv4 state without rewriting fixtures.
            with path.open("r+b", buffering=0) as stream:
                contents = stream.read(len(PAYLOAD) + 1)
            elapsed = time.monotonic() - started
            if contents != PAYLOAD:
                raise ValueError("Scratch fixture content/length mismatch")
            samples.append(elapsed)
    return {"p95_seconds": percentile95(samples, FIXTURES * PASSES), "samples": len(samples)}


class Supervisor:
    """Poll one isolated child; never wait/communicate on an unfinished process."""

    def __init__(self, spawn, interval=60, timeout=20):
        self.spawn = spawn
        self.interval = interval
        self.timeout = timeout
        self.child = None
        self.started = -math.inf
        self.timed_out = False
        self.lock = threading.Lock()
        self.values = {
            "success": 0, "samples": 0, "last_result_timestamp_seconds": 0,
            "last_success_timestamp_seconds": 0, "timeouts_total": 0, "child_blocked": 0,
        }

    def failure(self, wall):
        self.values.update(success=0, samples=0, last_result_timestamp_seconds=wall)
        self.values.pop("p95_seconds", None)

    def tick(self, now, wall):
        with self.lock:
            if self.child is not None:
                code = self.child.poll()
                if code is None:
                    if not self.timed_out and now - self.started >= self.timeout:
                        self.timed_out = True
                        self.failure(wall)
                        self.values["timeouts_total"] += 1
                        self.values["child_blocked"] = 1
                        try:
                            self.child.kill()
                        except ProcessLookupError:
                            pass
                    return
                if not self.timed_out:
                    try:
                        # Child emits a single tiny JSON result. Read only after exit.
                        payload = self.child.stdout.read(4097)
                        result = json.loads(payload) if len(payload) <= 4096 else {}
                        p95 = result["p95_seconds"]
                        if code or result["samples"] != FIXTURES * PASSES or not math.isfinite(p95) or p95 < 0:
                            raise ValueError("Invalid child result")
                        self.values.update(success=1, samples=result["samples"], p95_seconds=p95,
                                           last_result_timestamp_seconds=wall,
                                           last_success_timestamp_seconds=wall)
                    except (ValueError, KeyError, TypeError, OSError):
                        self.failure(wall)
                stdout = getattr(self.child, "stdout", None)
                if stdout is not None:
                    stdout.close()
                self.child = None
                self.values["child_blocked"] = 0
            if self.child is None and now - self.started >= self.interval:
                self.started = now
                self.timed_out = False
                try:
                    self.child = self.spawn()
                except OSError:
                    self.failure(wall)

    def metrics(self):
        with self.lock:
            lines = []
            for name, value in sorted(self.values.items()):
                kind = "counter" if name.endswith("_total") else "gauge"
                lines.extend([f"# HELP nfs_probe_{name} Scratch-only NFS probe {name}.",
                              f"# TYPE nfs_probe_{name} {kind}", f"nfs_probe_{name} {value}"])
            return "\n".join(lines) + "\n"


def make_server(supervisor, host, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/metrics", "/healthz"):
                self.send_error(404)
                return
            body = (supervisor.metrics() if self.path == "/metrics" else "ok\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return ThreadingHTTPServer((host, port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--root", default="/scratch")
    parser.add_argument("--port", type=int, default=9808)
    args = parser.parse_args()
    if args.child:
        # Every filesystem operation involving scratch belongs in this child.
        validate_mount(args.root, Path("/proc/self/mountinfo").read_text())
        print(json.dumps(measure(args.root, os.environ["NODE_NAME"], os.environ["POD_UID"])))
        return

    def spawn():
        return subprocess.Popen(
            [sys.executable, "-B", __file__, "--child", "--root", args.root],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    supervisor = Supervisor(spawn)
    server = make_server(supervisor, "0.0.0.0", args.port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    while True:
        supervisor.tick(time.monotonic(), time.time())
        time.sleep(0.25)


if __name__ == "__main__":
    main()
