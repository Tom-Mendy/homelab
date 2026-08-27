#!/usr/bin/env python3
"""Create a sanitized working-tree export for public publication."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


EXCLUDED_PREFIXES = (
    ".forgejo/",
    ".rumdl_cache/",
    "backlogs/",
    "docs/activity_report/",
    "docs/hermes/",
)

EXCLUDED_FILES = {
    "network_migration.md",
    "kubernetes/kube-config-documentation.md",
    "docs/acme-dns01-private-services.md",
    "docs/authentik-infisical-guest-checklist.md",
}

REPLACEMENTS = (
    ("forgejo.tom-mendy.com", "forgejo.example.com"),
    ("matrix.tom-mendy.com", "matrix.example.com"),
    ("home.tom-mendy.com", "home.example.com"),
    ("tom-mendy.com", "example.com"),
    ("92.222.90.223", "203.0.113.223"),
    ("192.168.1.", "198.51.100."),
    ("10.0.0" + ".11", "192.0.2.11"),
    ("10.0.0" + ".21", "192.0.2.21"),
    ("10.0.0" + ".22", "192.0.2.22"),
    ("10.0.0" + ".23", "192.0.2.23"),
    ("10.0.0" + ".53", "192.0.2.53"),
    ("10.0.0" + ".60-10.0.0" + ".89", "192.0.2.60-192.0.2.89"),
    ("10.0.0" + ".0/24", "192.0.2.0/24"),
    ("/volume1/k8s", "/export/kubernetes"),
)

FORBIDDEN_AFTER_SANITIZATION = (
    "tom-mendy.com",
    "192.168.1.",
    "10.0.0" + ".",
    "92.222.90.223",
    "/volume1/k8s",
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=True,
        capture_output=True,
    )
    return [Path(item) for item in result.stdout.decode().split("\0") if item]


def is_excluded(path: Path) -> bool:
    value = path.as_posix()
    return value in EXCLUDED_FILES or value.startswith(EXCLUDED_PREFIXES)


def sanitize(data: bytes) -> bytes:
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        return data

    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    content = re.sub(r"\b10\.0\.0\.(\d{1,3})\b", r"192.0.2.\1", content)
    return content.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory to create")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        print(f"refusing to overwrite existing path: {output}", file=sys.stderr)
        return 2

    output.mkdir(parents=True)
    copied = 0
    skipped = 0
    for source in tracked_files():
        if is_excluded(source):
            skipped += 1
            continue

        destination = output / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(sanitize(source.read_bytes()))
        copied += 1

    violations: list[str] = []
    for path in output.rglob("*"):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for forbidden in FORBIDDEN_AFTER_SANITIZATION:
            if forbidden in content:
                violations.append(f"{path.relative_to(output)} contains {forbidden}")

    if violations:
        shutil.rmtree(output)
        print("sanitization failed:", file=sys.stderr)
        print("\n".join(violations), file=sys.stderr)
        return 1

    print(f"created {output}")
    print(f"copied {copied} files; excluded {skipped} files")
    print("run a full-history secret scan before publishing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
