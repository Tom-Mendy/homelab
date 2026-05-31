# Remove Prometheus Legacy Manifests

## Problem

Prometheus had a local extras Helm chart and two legacy raw manifests for the
same ingress and storage resources:

- `kubernetes/prometheus/prometheus-ingress.yaml`
- `kubernetes/prometheus/prometheus-storage.yaml`

The Argo CD app already includes `path: kubernetes/prometheus`, so the local
chart is the desired source of truth for extras.

## Reasoning

Confirm Argo CD sources:

```sh
sed -n '1,140p' kubernetes/argocd/apps/prometheus.yaml
```

Confirm the local chart renders the same namespace, PV, PVC, and ingress:

```sh
helm template prometheus-local kubernetes/prometheus
```

## Changes

- Removed `kubernetes/prometheus/prometheus-ingress.yaml`.
- Removed `kubernetes/prometheus/prometheus-storage.yaml`.

## Outcome

Prometheus extras now have one declarative source: the local Helm chart under
`kubernetes/prometheus`.
