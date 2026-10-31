#!/usr/bin/env python3
"""Persist only user settings/authentication; never projects, databases or tools.

A native Kubernetes sidecar restores before the application starts and performs
its final sync after the application exits. Settings are copied, not symlinked:
applications may atomically replace config files. Runtime SQLite/WAL files stay
on the disposable home, never on NFS. No configuration contents are logged.
"""
import argparse
import os
from pathlib import Path
import signal
import stat
import tempfile
import threading

FILES = (
    ".t3/userdata/settings.json", ".t3/userdata/keybindings.json",
    ".t3/userdata/environment-id", ".t3/userdata/anonymous-id",
    ".t3/userdata/keybindings-migrations",
    ".codex/auth.json", ".codex/config.toml", ".codex/AGENTS.md", ".codex/instructions.md",
    ".local/share/opencode/auth.json", ".local/share/opencode/mcp-auth.json",
)
DIRECTORIES = (
    ".t3/userdata/secrets", ".t3/userdata/themes",
    ".codex/skills", ".codex/rules", ".config/opencode",
)
EXCLUDED = {"node_modules", ".git", "__pycache__", "logs", "log", "cache", "caches", "bin",
            "package-lock.json", "package.json", "bun.lock", "bun.lockb"}


def configuration_files(root):
    root = Path(root)
    selected = set()
    for name in FILES:
        path = root / name
        if path.is_file() and not path.is_symlink():
            selected.add(Path(name))
    for directory in DIRECTORIES:
        start = root / directory
        if not start.is_dir() or start.is_symlink():
            continue
        for parent, dirs, files in os.walk(start, followlinks=False):
            parent = Path(parent)
            dirs[:] = [name for name in dirs if name not in EXCLUDED and not (parent / name).is_symlink()]
            for name in files:
                path = parent / name
                if name not in EXCLUDED and not path.is_symlink() and path.is_file() and not any(
                    suffix in name for suffix in (".sqlite", ".db-wal", ".db-shm")) and not name.endswith(".db"):
                    selected.add(path.relative_to(root))
    return selected


def sync_configs(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    paths = configuration_files(source)
    for relative in sorted(paths):
        original, target = source / relative, destination / relative
        if not original.is_file():
            continue  # an application atomically replaced/deleted it during scan
        payload = original.read_bytes()
        mode = 0o700 if original.stat().st_mode & stat.S_IXUSR else 0o600
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if target.is_file() and not target.is_symlink() and target.read_bytes() == payload:
            continue
        fd, temporary = tempfile.mkstemp(prefix=".settings-sync-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                os.fchmod(handle.fileno(), mode)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    for relative in configuration_files(destination) - paths:
        (destination / relative).unlink(missing_ok=True)
    return len(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "restore", "watch"))
    parser.add_argument("--home", type=Path, default=Path("/home/coder"))
    parser.add_argument("--persist", type=Path, default=Path("/settings"))
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()
    os.umask(0o077)
    if args.action == "snapshot":
        print("Configuration files saved:", sync_configs(args.home, args.persist), flush=True)
        return
    count = sync_configs(args.persist, args.home)
    print("Configuration files restored:", count, flush=True)
    if args.action == "restore":
        return
    (args.home / ".config-sync-ready").touch(mode=0o600)
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    while not stopped.wait(args.interval):
        try:
            sync_configs(args.home, args.persist)
        except OSError as error:
            print("Configuration sync failed:", type(error).__name__, flush=True)
    print("Final configuration files saved:", sync_configs(args.home, args.persist), flush=True)


if __name__ == "__main__":
    main()
