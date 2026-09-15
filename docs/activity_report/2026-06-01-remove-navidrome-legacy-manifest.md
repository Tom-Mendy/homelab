# Remove Navidrome Legacy Manifest

## Problem

Navidrome had both a local Helm chart and a legacy raw manifest. Argo CD points
at `kubernetes/navidrome`, so the chart is the desired source of truth.
Keeping `kubernetes/navidrome/navidrome.yaml` created drift risk.

## Reasoning

Confirm Argo CD source:

```sh
sed -n '1,120p' kubernetes/argocd/apps/navidrome.yaml
```

Confirm the chart renders the same workload, storage, service, and ingress
surface:

```sh
helm template navidrome kubernetes/navidrome
```

The rendered chart contains:

- Namespace `navidrome`
- PV `navidrome-music-pv`
- PVCs `navidrome-music-pvc` and `navidrome-data-pvc`
- Deployment `navidrome`
- Service `navidrome`
- Ingress `navidrome-ingress`

## Changes

- Removed `kubernetes/navidrome/navidrome.yaml`.

## Outcome

Navidrome now has one declarative source in the repository: the local Helm chart
under `kubernetes/navidrome`.

Validation:

```text
helm template navidrome kubernetes/navidrome
kubectl apply --dry-run=server -f /tmp/navidrome-render.yaml
namespace/navidrome configured (server dry run)
persistentvolume/navidrome-music-pv configured (server dry run)
persistentvolumeclaim/navidrome-music-pvc configured (server dry run)
persistentvolumeclaim/navidrome-data-pvc configured (server dry run)
service/navidrome configured (server dry run)
deployment.apps/navidrome configured (server dry run)
ingress.networking.k8s.io/navidrome-ingress configured (server dry run)
```
