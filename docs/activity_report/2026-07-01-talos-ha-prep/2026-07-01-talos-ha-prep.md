# Talos HA migration preparation

## Problem

The homelab will move from an Ubuntu Kubernetes cluster to a clean Talos
cluster. All three machines will become both control-plane and worker nodes:

- `node1`: `10.0.0.21`
- `node2`: `10.0.0.22`
- `node3`: `10.0.0.23`

The Kubernetes API endpoint must be reachable before in-cluster DNS or MetalLB
exists, and existing `nfs-k8s` data must be rebound instead of reprovisioned
into empty NFS directories.

## Reasoning

The DNS endpoint was created in Cloudflare as DNS-only records:

- `kube.home.tom-mendy.com -> 10.0.0.21`
- `kube.home.tom-mendy.com -> 10.0.0.22`
- `kube.home.tom-mendy.com -> 10.0.0.23`

Because these are private LAN IPs, the name only works from the LAN or VPN. That
is fine for Talos bootstrap because the workstation and nodes are on the LAN.

Talos secrets and machine configs were generated outside the repository under:

```text
~/.talos/homelab-talos-2026-07-01
```

The generated configs intentionally use an invalid install disk placeholder:

```text
/dev/disk/by-id/REPLACE_ME_AFTER_TALOS_ISO_DISK_CHECK
```

This prevents accidental installation before each node's real disk is confirmed
from the Talos ISO.

## Commands and results

DNS and node reachability:

```sh
getent ahostsv4 kube.home.tom-mendy.com
nslookup kube.home.tom-mendy.com
host kube.home.tom-mendy.com
ping -c 2 10.0.0.21
ping -c 2 10.0.0.22
ping -c 2 10.0.0.23
```

Results:

```text
kube.home.tom-mendy.com resolved to 10.0.0.21, 10.0.0.22, 10.0.0.23.
All three node IPs answered ping with 0% packet loss.
```

Local tool check:

```sh
command -v talosctl
command -v helm
command -v yq
```

Result:

```text
talosctl, helm, and yq were not installed directly in the shell.
```

Use Nix tooling without adding repo dependencies:

```sh
nix shell nixpkgs#talosctl nixpkgs#kubernetes-helm nixpkgs#yq-go \
  nixpkgs#dnsutils --command sh -c \
  'talosctl version --client && helm version --short && yq --version'
```

Result:

```text
talosctl v1.13.4
helm v3.20.2
yq v4.53.2
```

Generated Talos secrets and config files outside the repo:

```sh
talosctl gen secrets -o secrets.yaml
talosctl gen config \
  --with-secrets secrets.yaml \
  --install-disk /dev/disk/by-id/REPLACE_ME_AFTER_TALOS_ISO_DISK_CHECK \
  --additional-sans kube.home.tom-mendy.com \
  --additional-sans 10.0.0.21 \
  --additional-sans 10.0.0.22 \
  --additional-sans 10.0.0.23 \
  --config-patch-control-plane @allow-controlplane-workloads.patch.yaml \
  --output base \
  --force \
  homelab-talos https://kube.home.tom-mendy.com:6443
talosctl machineconfig patch base/controlplane.yaml \
  --patch @node1.patch.yaml \
  --output controlplane-node1.yaml
talosctl machineconfig patch base/controlplane.yaml \
  --patch @node2.patch.yaml \
  --output controlplane-node2.yaml
talosctl machineconfig patch base/controlplane.yaml \
  --patch @node3.patch.yaml \
  --output controlplane-node3.yaml
```

Generated files:

```text
~/.talos/homelab-talos-2026-07-01/secrets.yaml
~/.talos/homelab-talos-2026-07-01/base/talosconfig
~/.talos/homelab-talos-2026-07-01/controlplane-node1.yaml
~/.talos/homelab-talos-2026-07-01/controlplane-node2.yaml
~/.talos/homelab-talos-2026-07-01/controlplane-node3.yaml
```

Validated non-secret fields:

```text
controlplane-node1.yaml:
  hostname: node1
  endpoint: https://kube.home.tom-mendy.com:6443
  allowSchedulingOnControlPlanes: true

controlplane-node2.yaml:
  hostname: node2
  endpoint: https://kube.home.tom-mendy.com:6443
  allowSchedulingOnControlPlanes: true

controlplane-node3.yaml:
  hostname: node3
  endpoint: https://kube.home.tom-mendy.com:6443
  allowSchedulingOnControlPlanes: true
  gpu: "true"
```

Exported non-secret current cluster state:

```sh
kubectl get nodes -o wide
kubectl get storageclass -o yaml
kubectl get pv -o yaml
kubectl get pvc -A -o yaml
kubectl get applications -n argocd -o yaml
kubectl get clusters.postgresql.cnpg.io -A -o yaml
```

Export path:

```text
~/.talos/homelab-talos-2026-07-01/current-cluster-export
```

Generated the static rebinding manifest for existing dynamic `nfs-k8s` data:

```text
~/.talos/homelab-talos-2026-07-01/restore-nfs-k8s-static-bindings.yaml
```

Result:

```text
43 objects generated:
- namespaces needed by the prebound PVCs
- static PVs for existing dynamic nfs-k8s NFS paths
- PVCs with volumeName set to the existing PV names
```

The restore manifest itself contains no `local-path` references.

## Final outcome

The next Talos migration step is ready but still intentionally non-destructive.

Before applying any machine config to a node:

1. Boot that node into the Talos ISO.
2. Run `talosctl get disks --insecure --nodes <node-ip>`.
3. Replace the install disk placeholder in that node's config with the correct
   disk path.
4. Only then run `talosctl apply-config --insecure`.

No node was drained, rebooted, reinstalled, or modified during this preparation.
