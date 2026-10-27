"""Keep downloadable CLI binaries off NFS without moving persistent user data."""

import fcntl
import time
from pathlib import Path


def prepare_cache(source: Path, cache: Path) -> None:
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    source.parent.mkdir(parents=True, exist_ok=True)

    with (cache.parent / "prepare-runtime.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if source.is_symlink() and source.resolve() == cache.resolve():
            return

        if source.exists() or source.is_symlink():
            backup = source.with_name(f"{source.name}.nfs-backup-{time.time_ns()}")
            source.rename(backup)
            print(f"Previous executable cache retained at {backup}", flush=True)

        source.symlink_to(cache, target_is_directory=True)
        print(f"CLI executable cache: {source} -> {cache}", flush=True)


if __name__ == "__main__":
    home = Path.home()
    prepare_cache(home / ".t3/runtime", Path("/tmp/t3code-local/runtime"))
    prepare_cache(home / ".codex/packages/standalone", Path("/tmp/codex-local/standalone"))
    prepare_cache(home / ".opencode/bin", Path("/tmp/opencode-local/bin"))
