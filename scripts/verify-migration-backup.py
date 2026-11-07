#!/usr/bin/env python3
"""Validate an age-encrypted tar.gz or ZIP without printing protected contents."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import zipfile


def verify(archive, identity, age, extract_to=None, check_sqlite=False):
    if check_sqlite and extract_to is None:
        raise ValueError("SQLite validation requires --extract-to")
    if extract_to is not None:
        extract_to.mkdir(mode=0o700, parents=True, exist_ok=True)
        if any(extract_to.iterdir()):
            raise ValueError("Extraction directory must be empty")

    result = {"archive": archive.name, "files": 0, "sqlite": [], "verified_blobs": 0}
    with tempfile.TemporaryDirectory(prefix="homelab-backup-verify-") as temporary:
        # stderr remains private and is never included in command output.
        with (Path(temporary) / "age.log").open("wb") as errors:
            process = subprocess.Popen(
                [age, "--decrypt", "--identity", str(identity), str(archive)],
                stdout=subprocess.PIPE,
                stderr=errors,
            )
            try:
                if archive.name.endswith(".tar.gz.age"):
                    with gzip.GzipFile(fileobj=process.stdout, mode="rb") as decoded:
                        with tarfile.open(fileobj=decoded, mode="r|") as contents:
                            for member in contents:
                                expected = _blob_digest(member.name)
                                if expected is not None and not member.isfile():
                                    raise ValueError("Blob payload is not a regular file")
                                if extract_to is not None:
                                    contents.extract(member, extract_to, filter="data")
                                    if member.isfile() and expected is not None:
                                        with (extract_to / member.name).open("rb") as source:
                                            _verify_blob(source, expected)
                                        result["verified_blobs"] += 1
                                elif member.isfile():
                                    with contents.extractfile(member) as source:
                                        if expected is None:
                                            shutil.copyfileobj(source, _Discard())
                                        else:
                                            _verify_blob(source, expected)
                                            result["verified_blobs"] += 1
                                if member.isfile():
                                    result["files"] += 1
                        # tar EOF can precede gzip EOF. Consume the trailer so a
                        # missing footer or invalid CRC cannot look successful.
                        shutil.copyfileobj(decoded, _Discard())
                elif archive.name.endswith(".zip.age"):
                    payload = Path(temporary) / "backup.zip"
                    with payload.open("wb") as target:
                        shutil.copyfileobj(process.stdout, target)
                    with zipfile.ZipFile(payload) as contents:
                        if contents.testzip() is not None:
                            raise ValueError("ZIP member CRC validation failed")
                        for member in contents.infolist():
                            path = Path(member.filename)
                            if path.is_absolute() or ".." in path.parts:
                                raise ValueError("Unsafe ZIP member path")
                            if extract_to is not None:
                                contents.extract(member, extract_to)
                            if not member.is_dir():
                                result["files"] += 1
                else:
                    raise ValueError("Expected a .tar.gz.age or .zip.age archive")
                if process.wait() != 0:
                    raise ValueError("age authentication or decryption failed")
            except BaseException:
                process.kill()
                process.wait()
                raise

    if check_sqlite:
        # Extract the complete snapshot before opening databases, including WAL
        # files when present. Never apply immutable=1 to a WAL-backed snapshot.
        for path in sorted(extract_to.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            if path.suffix not in {".db", ".sqlite", ".sqlite3"}:
                continue
            with path.open("rb") as source:
                if source.read(16) != b"SQLite format 3\x00":
                    continue
            database = sqlite3.connect(path)
            try:
                database.execute("PRAGMA query_only=ON")
                if database.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ValueError("SQLite integrity check failed")
            finally:
                database.close()
            result["sqlite"].append(str(path.relative_to(extract_to)))

    digest = hashlib.sha256()
    with archive.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    result.update({"sha256": digest.hexdigest(), "verified": True})
    return result


class _Discard:
    def write(self, data):
        return len(data)


def _blob_digest(name):
    # Recognize the fixed volume layouts used by Distribution and Ollama.
    match = re.fullmatch(
        r"data/docker/registry/v2/blobs/sha256/([0-9a-f]{2})/([0-9a-f]{64})/data",
        name,
    )
    if match is not None:
        if match[1] != match[2][:2]:
            raise ValueError("Registry blob is stored under an invalid prefix")
        return match[2]
    match = re.fullmatch(r"data/models/blobs/sha256-([0-9a-f]{64})", name)
    return match[1] if match is not None else None


def _verify_blob(source, expected):
    digest = hashlib.sha256()
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("Content-addressed blob checksum mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--identity", required=True, type=Path)
    parser.add_argument("--age", default="age")
    parser.add_argument("--extract-to", type=Path)
    parser.add_argument("--check-sqlite", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(
            args.archive, args.identity, args.age, args.extract_to, args.check_sqlite
        )
    except (OSError, ValueError, EOFError, tarfile.TarError, zipfile.BadZipFile,
            sqlite3.DatabaseError):
        parser.exit(1, "Backup verification failed; keep the source unchanged.\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
