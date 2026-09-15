# Remove Ollama Legacy Manifests

## Problem

Ollama had a local Helm chart plus legacy raw manifests for GPU support and
ingress:

- `kubernetes/ollama/nvidia-device-plugin.yaml`
- `kubernetes/ollama/ollama-ingress.yaml`
- `kubernetes/ollama/runtimeclass-nvidia.yaml`

The Argo CD app uses `path: kubernetes/ollama` with Helm rendering, so the chart
is the desired source of truth.

## Reasoning

Confirm Argo CD source:

```sh
sed -n '1,140p' kubernetes/argocd/apps/ollama.yaml
```

Confirm the chart renders the same GPU and ingress resources:

```sh
helm template ollama kubernetes/ollama
```

The rendered chart contains:

- RuntimeClass `nvidia`
- NVIDIA device plugin ServiceAccount, RBAC, and DaemonSet
- Deployment `ollama`
- Service `ollama`
- Ingress `ollama-ingress`
- PVC `ollama-data`

## Changes

- Removed legacy raw Ollama GPU and ingress manifests.

## Outcome

Ollama now has one declarative source in the repository: the local Helm chart
under `kubernetes/ollama`.
