# Remove Blocky Legacy Manifest

## Problem

Blocky had both a local Helm chart and a legacy raw manifest. The Argo CD app
points at `kubernetes/blocky`, so the chart is the desired source of truth.
Keeping `kubernetes/blocky/blocky.yaml` created drift risk.

The chart also had two ConfigMap templates rendering the same `blocky-config`
object.

## Reasoning

Confirm Argo CD source:

```sh
sed -n '1,120p' kubernetes/argocd/apps/blocky.yaml
```

Confirm the chart renders the same workload/service surface:

```sh
helm template blocky kubernetes/blocky
```

The rendered chart contains:

- Namespace `blocky`
- ConfigMap `blocky-config`
- Deployment `blocky`
- LoadBalancer Service `blocky`

## Changes

- Removed `kubernetes/blocky/blocky.yaml`.
- Removed duplicate `kubernetes/blocky/templates/configmap.tpl`.
- Updated the ACME DNS-01 doc to use Helm chart commands instead of raw
  `kubectl apply -f` commands for Blocky, Navidrome, and Vaultwarden.

## Outcome

Blocky now has one declarative source in the repository: the local Helm chart
under `kubernetes/blocky`.

Validation:

```text
helm template blocky kubernetes/blocky
kubectl apply --dry-run=server -f /tmp/blocky-render.yaml
namespace/blocky configured (server dry run)
configmap/blocky-config configured (server dry run)
service/blocky configured (server dry run)
deployment.apps/blocky configured (server dry run)
```
