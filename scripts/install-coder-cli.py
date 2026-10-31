#!/usr/bin/env python3
"""Install a pinned Coder CLI from its release, without piping remote shell code.

The coder.com bootstrap endpoint failed TLS in the Forgejo runner. Download
bounded/retried GitHub release artifacts instead, verify SHA-256, and extract
only the executable. The release checksum is obtained over HTTPS from the same
official release; this is integrity checking, not independent signature trust.
"""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile


def install_verified(archive, checksums, target):
    archive, checksums, target = Path(archive), Path(checksums), Path(target)
    entries = [line.split() for line in checksums.read_text().splitlines()]
    expected = [row[0] for row in entries if len(row) == 2 and row[1].lstrip("*") == archive.name]
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if len(expected) != 1 or not re.fullmatch(r"[0-9a-fA-F]{64}", expected[0]) or digest != expected[0].lower():
        raise ValueError("Official release SHA-256 mismatch or missing checksum")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as bundle:
        executables = [item for item in bundle.getmembers() if item.name in ("coder", "./coder")]
        if len(executables) != 1:
            raise ValueError("Release must contain exactly one root-level Coder executable")
        member = executables[0]
        if not member.isfile():
            raise ValueError("Release executable must be a regular file")
        source = bundle.extractfile(member)
        if source is None:
            raise ValueError("Release executable is missing")
        fd, temporary = tempfile.mkstemp(prefix=".coder-install-", dir=target.parent)
        try:
            with source, os.fdopen(fd, "wb") as output:
                shutil.copyfileobj(source, output)
                os.fchmod(output.fileno(), 0o755)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=os.environ.get("CODER_CLI_VERSION", "2.36.4"))
    parser.add_argument("--directory", type=Path, default=Path.home() / ".local/bin")
    args = parser.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        parser.error("Version must be a pinned stable major.minor.patch")
    architectures = {"x86_64": "amd64", "aarch64": "arm64"}
    if platform.system() != "Linux" or platform.machine() not in architectures:
        parser.error("This installer supports Linux amd64/arm64")
    name = f"coder_{args.version}_linux_{architectures[platform.machine()]}.tar.gz"
    sums = f"coder_{args.version}_checksums.txt"
    base = f"https://github.com/coder/coder/releases/download/v{args.version}"
    with tempfile.TemporaryDirectory(prefix="coder-release-") as directory:
        root = Path(directory)
        for filename in (sums, name):
            subprocess.run([
                "curl", "--fail", "--location", "--silent", "--show-error",
                "--retry", "3", "--retry-all-errors", "--retry-max-time", "240",
                "--connect-timeout", "15", "--max-time", "180",
                "--output", str(root / filename), base + "/" + filename,
            ], check=True, timeout=260)
        target = args.directory.expanduser().resolve() / "coder"
        install_verified(root / name, root / sums, target)
    subprocess.run([str(target), "version"], check=True, timeout=30)


if __name__ == "__main__":
    main()
