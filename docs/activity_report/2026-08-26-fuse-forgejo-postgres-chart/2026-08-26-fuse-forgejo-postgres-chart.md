# Fuse Forgejo and PostgreSQL into one Helm chart

## Problem

Forgejo and its CloudNativePG PostgreSQL cluster were maintained as two local
Helm charts and two Flux `HelmRelease` objects. The requested layout has one
chart at `kubernetes/forgejo` and one release that owns both workloads.

The PostgreSQL Cluster and its generated application Secret must keep their
current names. The database uses the shared `nfs-k8s` storage class and must not
move to worker-local storage during the change.

## Reasoning path

Inspect the current chart files and Flux references:

```sh
find kubernetes/forgejo kubernetes/forgejo-postgres -maxdepth 3 -type f -print
rg -n 'forgejo-postgres|kubernetes/forgejo-postgres' kubernetes
sed -n '230,305p' kubernetes/flux/cluster/apps/applications.yaml
```

The Forgejo chart already referenced the PostgreSQL service and Secret. The
PostgreSQL chart only contained one CloudNativePG `Cluster` template and its
values. I copied that template into the Forgejo chart, added the values and
schema there, and removed the second chart from the active chart list.

Helm ownership must be migrated before deleting the old release. The safe
sequence is:

```sh
flux suspend helmrelease forgejo-postgres -n flux-system
kubectl annotate cluster forgejo-postgres -n forgejo \
  meta.helm.sh/release-name=forgejo \
  meta.helm.sh/release-namespace=forgejo --overwrite
kubectl label cluster forgejo-postgres -n forgejo \
  app.kubernetes.io/managed-by=Helm --overwrite
flux reconcile kustomization flux-system -n flux-system --with-source
```

The first inspection used the wrong namespace for the HelmReleases:

```text
$ kubectl get helmrelease -n forgejo forgejo forgejo-postgres
Error from server (NotFound):
helmreleases.helm.toolkit.fluxcd.io "forgejo" not found
```

The HelmReleases are managed in `flux-system`, while their workloads target
`forgejo`. A second inspection from an authorized Kubernetes connection showed
both releases ready, the Cluster healthy, the PostgreSQL PVC bound to
`nfs-k8s`, and the Forgejo Deployment available. The old release was suspended
and the existing Cluster was annotated and labeled for the `forgejo` release
before the new chart was reconciled.

## Validation results

The combined chart renders the Forgejo Deployment and the PostgreSQL Cluster:

```sh
helm lint kubernetes/forgejo
```

```text
1 chart(s) linted, 0 chart(s) failed
```

```sh
./scripts/test-helm-chart.sh
```

```text
=== forgejo ===
OK
...
=== vaultwarden ===
OK
```

The storage policy check passed:

```sh
./scripts/check-storage-policy.sh
```

```text
storage policy ok
```

Flux applied the merged release configuration:

```sh
flux reconcile kustomization flux-system -n flux-system --with-source
```

```text
fetched revision refs/heads/main@sha1:3d331a1c28dbcf088f3e0c4b909a0c188edfc91e
applied revision refs/heads/main@sha1:3d331a1c28dbcf088f3e0c4b909a0c188edfc91e
```

The final live state is:

```text
forgejo HelmRelease       True  0.2.0+3d331a1c28db
forgejo-postgres          absent
forgejo-postgres Cluster  Cluster in healthy state  1/1
forgejo-postgres PVC      Bound  nfs-k8s
forgejo Deployment        1 ready, 1 available
forgejo-postgres-app      Secret exists
```

The local kubeconform binary is not installed:

```sh
./scripts/render-local-charts-for-kubeconform.sh /tmp/forgejo-fused-render-dir
kubeconform is required but was not found in PATH
```

The Forgejo activity report passes Markdown validation. The repository-wide
`rumdl check --fix .` command still reports pre-existing issues in unrelated
files and made no changes.

## Final outcome

`kubernetes/forgejo` now contains the Forgejo resources and the CloudNativePG
Cluster. The old `kubernetes/forgejo-postgres` chart and Flux `HelmRelease` are
removed, and the Forgejo release depends directly on `cloudnative-pg`.

The existing Cluster, PVC, Secret, and Deployment survived the ownership
transfer. Only `HelmRelease/forgejo` remains for this application.
