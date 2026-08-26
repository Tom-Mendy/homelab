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
flux suspend helmrelease forgejo-postgres -n forgejo
kubectl annotate cluster forgejo-postgres -n forgejo \
  meta.helm.sh/release-name=forgejo \
  meta.helm.sh/release-namespace=forgejo --overwrite
kubectl label cluster forgejo-postgres -n forgejo \
  app.kubernetes.io/managed-by=Helm --overwrite
flux reconcile kustomization apps -n flux-system --with-source
```

The live adoption sequence could not be run from this environment:

```text
$ kubectl get helmrelease -n forgejo forgejo forgejo-postgres
Unable to connect to the server: dial tcp 10.0.0.21:6443: socket: operation not permitted
```

The repository change therefore includes the `helm.sh/resource-policy: keep`
annotation on the Cluster. This protects the database resource if the old
release is removed before the new release adopts it.

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

Before allowing Flux to delete the old release, run the adoption commands above
and verify that `Cluster/forgejo-postgres`, its PVC, Secret, and the Forgejo
Deployment are healthy. Then confirm that only `HelmRelease/forgejo` remains.
