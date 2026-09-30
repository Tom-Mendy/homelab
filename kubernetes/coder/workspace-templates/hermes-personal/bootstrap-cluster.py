"""Install verified cluster clients and configure the Hermes local terminal."""

import hashlib
import io
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

import yaml


# kubectl matches the documented Kubernetes 1.34 control plane.
# Keep checksums pinned here, rather than trusting downloads at workspace startup.
TOOLS = {
    "kubectl": (
        "1.34.12",
        "https://dl.k8s.io/release/v1.34.12/bin/linux/amd64/kubectl",
        "90b7b9058ffeb5c10710bb1c73f541eaf426fb1b4e87df435db669de9a2564a2",
        None,
    ),
    "helm": (
        "3.22.0",
        "https://get.helm.sh/helm-v3.22.0-linux-amd64.tar.gz",
        "1e4ab49e429626cf6c6958d914248b78c9730803c2751b87627e171dc800e7bb",
        "linux-amd64/helm",
    ),
    "flux": (
        "2.9.5",
        "https://github.com/fluxcd/flux2/releases/download/v2.9.5/flux_2.9.5_linux_amd64.tar.gz",
        "b853df82adfd7736f580692f9f734473d571606307139f8fd20c2a80dd1ff473",
        "flux",
    ),
    "jq": (
        "1.8.2",
        "https://github.com/jqlang/jq/releases/download/jq-1.8.2/jq-linux-amd64",
        "b1c22172dd303f3be49e935aa56aa48a8b7a46e0bc838b4997d3bb451495870f",
        None,
    ),
}


def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(data)
            output.flush()
            os.fchmod(output.fileno(), mode)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def install_tools(home):
    bin_dir = home / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name, (version, url, checksum, member) in TOOLS.items():
        cached = home / ".local/share/hermes-cluster-tools" / f"{name}-{version}"
        if not cached.is_file():
            print(f"Installing {name} {version}", flush=True)
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != checksum:
                raise ValueError(f"Checksum mismatch for {name}")
            if member:
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise ValueError(f"Missing archive member for {name}")
                    data = stream.read()
            atomic_write(cached, data, 0o755)
        link = bin_dir / name
        if link.is_symlink() and link.resolve() == cached.resolve():
            continue
        link.unlink(missing_ok=True)
        link.symlink_to(cached)


def configure_terminal(hermes_home):
    config_path = hermes_home / "config.yaml"
    if not config_path.exists():
        return
    config = yaml.safe_load(config_path.read_text()) or {}
    terminal = config.setdefault("terminal", {})
    terminal["backend"] = "local"
    terminal["cwd"] = str(hermes_home)
    # Matrix and scheduled jobs must be able to run commands, too.
    platform_toolsets = config.setdefault("platform_toolsets", {})
    for platform in ("matrix", "cron"):
        enabled = platform_toolsets.setdefault(platform, ["hermes-cli"])
        if "hermes-cli" not in enabled:
            enabled.append("hermes-cli")
    disabled = config.setdefault("agent", {}).get("disabled_toolsets", [])
    for toolset in ("terminal", "file", "hermes-cli"):
        if toolset in disabled:
            disabled.remove(toolset)
    backup = config_path.with_name("config.before-cluster-access.yaml")
    if not backup.exists():
        shutil.copyfile(config_path, backup)
        backup.chmod(0o600)
    atomic_write(config_path, yaml.safe_dump(config, sort_keys=False).encode(), 0o600)


def configure_kubeconfig(home):
    service_account = "/var/run/secrets/kubernetes.io/serviceaccount"
    config = {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [{"name": "homelab", "cluster": {
            "server": "https://kubernetes.default.svc",
            "certificate-authority": f"{service_account}/ca.crt",
        }}],
        "users": [{"name": "hermes", "user": {
            "tokenFile": f"{service_account}/token",
        }}],
        "contexts": [{"name": "homelab", "context": {
            "cluster": "homelab", "user": "hermes", "namespace": "default",
        }}],
        "current-context": "homelab",
    }
    atomic_write(home / ".kube/hermes.config", yaml.safe_dump(config).encode(), 0o600)


def main():
    configure_kubeconfig(Path(os.environ["HOME"]))
    install_tools(Path(os.environ["HOME"]))
    configure_terminal(Path(os.environ["HERMES_HOME"]))


if __name__ == "__main__":
    main()
