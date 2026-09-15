# Personal Coder desktop workspace

## Problem

Tom needs a persistent graphical development workspace that remains available
when his personal laptop is offline. The existing Coder templates expose
terminal-oriented Hermes and T3 workspaces, but no browser-accessible desktop.

## Implementation

A dedicated `personal-desktop` Coder template was added. It uses a custom
Forgejo-built image based on the existing pinned Hermes image and installs XFCE,
TigerVNC, noVNC/websockify, Chromium, shell tooling, and development
prerequisites at image build time. The runtime remains UID/GID 10000 and does
not receive a Kubernetes service-account token or privilege escalation.

The template creates a 50Gi `nfs-k8s` PVC mounted at `/opt/data` and exposes
only a Coder owner-only application named `Desktop` at localhost:6080. There is
no direct VNC Ingress, NodePort, or LoadBalancer. The stable public entry point
is `https://coder.home.tom-mendy.com`; Coder generates the authenticated app
link from the workspace dashboard.

## Files

- `.forgejo/workflows/personal-desktop-image.yml`: builds and publishes the
  image to `forgejo.tom-mendy.com`.
- `kubernetes/coder/workspace-images/personal-desktop/Dockerfile`: reproducible
  non-root desktop image.
- `kubernetes/coder/workspace-images/personal-desktop/start-desktop.sh`: starts
  an idempotent XFCE/TigerVNC/noVNC session.
- `kubernetes/coder/workspace-templates/personal-desktop/main.tf`: Coder agent,
  owner-only desktop app, PVC, and Deployment.

## Validation and rollout

Run these commands from the repository root after checkout:

```sh
docker build --pull \
  --file kubernetes/coder/workspace-images/personal-desktop/Dockerfile \
  --tag personal-desktop:test \
  kubernetes/coder/workspace-images/personal-desktop

terraform -chdir=kubernetes/coder/workspace-templates/personal-desktop fmt -check
terraform -chdir=kubernetes/coder/workspace-templates/personal-desktop init -backend=false
terraform -chdir=kubernetes/coder/workspace-templates/personal-desktop validate
./scripts/check-storage-policy.sh

coder login https://coder.home.tom-mendy.com
coder templates push personal-desktop \
  --directory kubernetes/coder/workspace-templates/personal-desktop
```

After the image workflow succeeds, create one workspace named
`tom-personal-desktop`, open its `Desktop` app, stop/start it, and confirm that
files under `/opt/data` persist. Test the workspace from a second computer.

The workspace is CPU-only and cannot use the G14's local RTX GPU. GPU-backed
ComfyUI remains a separate concern.
