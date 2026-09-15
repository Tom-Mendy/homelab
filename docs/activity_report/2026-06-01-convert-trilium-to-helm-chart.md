# Convert Trilium to Helm Chart

## Problem

Trilium was still managed by a raw manifest at `kubernetes/trilium/trilium.yaml`.
The repo convention is local Helm charts for app manifests where that reduces
drift and makes values explicit.

## Reasoning

Inspect the Argo CD app:

```sh
sed -n '1,160p' kubernetes/argocd/apps/trilium.yaml
```

Inspect the live resources before conversion:

```sh
kubectl get deploy,svc,ingress -n default trilium -o yaml
```

The live resource surface was:

- Deployment `default/trilium`
- Service `default/trilium`
- Ingress `default/trilium`

The Deployment had no PVC or volume mounts. The generated chart keeps the same
resource names, namespace, labels, image, environment variable, service port,
and ingress host.

## Changes

- Removed `kubernetes/trilium/trilium.yaml`.
- Added a local Helm chart under `kubernetes/trilium`.
- Added `values.yaml` and `values.schema.json` for the existing deployment,
  service, ingress, image, and annotations.

## Outcome

Trilium now follows the local chart pattern used by other apps. Argo CD still
points at `kubernetes/trilium`, so no Argo Application change is needed.

Validation:

```text
helm template trilium kubernetes/trilium
kubectl apply --dry-run=server -f /tmp/trilium-render.yaml
service/trilium configured (server dry run)
deployment.apps/trilium configured (server dry run)
ingress.networking.k8s.io/trilium configured (server dry run)

./kubernetes/test-helm-chart.sh
=== trilium ===
OK

storage policy ok
```
