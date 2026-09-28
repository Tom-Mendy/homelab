# Homelab Kubernetes platform

Infrastructure as code for a three-node Kubernetes homelab. The cluster is
managed with Flux GitOps and runs platform services, self-hosted applications,
databases, CI runners, and an internal developer environment.

This repository shows how I operate a small platform over time: changes are
reviewed in Git, rendered and checked in CI, reconciled by Flux, and backed by
recovery procedures. It is an operational project, not a generic Kubernetes
starter template.

## What the project demonstrates

- GitOps reconciliation with Flux, Helm releases, and Kustomize.
- Local Helm charts for project-specific Kubernetes resources.
- Identity and SSO with Authentik and OIDC.
- Runtime secret delivery with Infisical, without committing credentials.
- PostgreSQL clusters managed by CloudNativePG.
- Shared NFS-backed persistent storage that is independent of worker nodes.
- Ingress and TLS routing with Traefik.
- Observability with Prometheus and Grafana.
- Forgejo Actions and GitHub Actions runners for CI workloads.
- Validation gates for secret scanning, Helm rendering, Kubernetes schemas,
  and storage policy.
- Backup, restore, node maintenance, and disaster recovery runbooks.

## Architecture at a glance

The live cluster has one control-plane node and two workers:

| Area | Implementation |
| --- | --- |
| Nodes | `node1` control plane, `node2` and `node3` workers |
| Reconciliation | Flux Operator, Flux controllers, native Flux resources |
| Git source | Private Forgejo repository inside the cluster |
| Ingress | Traefik |
| Identity | Authentik with OIDC integrations |
| Secrets | Infisical Operator and external secret resources |
| Databases | CloudNativePG PostgreSQL clusters |
| Persistent storage | Synology NFS at `10.0.0.11:/volume1/k8s`, exposed as `nfs-k8s` |
| Observability | Prometheus and Grafana |

The dependency direction is deliberate. Flux applies platform services first.
Identity, storage, and database releases then provide prerequisites for
application releases. HelmReleases declare these dependencies with `dependsOn`.

See [`docs/architecture.md`](docs/architecture.md) for the component map and
deployment flow. The repository contains environment-specific values for the
live homelab, so review [`docs/publication.md`](docs/publication.md) before
sharing a copy publicly.

## Repository layout

```text
homelab/
├── kubernetes/
│   ├── flux/                 # Flux bootstrap and cluster reconciliation
│   ├── <service>/            # Local Helm charts and service configuration
│   └── active-local-charts.txt
├── docs/                     # Architecture, operations, and recovery runbooks
├── scripts/                  # Rendering, validation, and hardware utilities
├── .forgejo/workflows/       # CI validation and image build workflows
├── CONTRIBUTING.md
└── README.md
```

The `kubernetes/` directory contains both local charts and values consumed by
external charts. `kubernetes/flux/cluster/` is the entry point for steady-state
reconciliation. `active-local-charts.txt` defines the charts rendered by the
local validation scripts.

## Getting started

### Validate changes locally

This is the safe starting point. It does not require cluster access.

Prerequisites:

- Bash, Helm 3, and kubeconform.
- `rumdl` for Markdown checks.
- `kubectl` only if you also want to render or validate Kustomize resources.

Run the same core checks used by Forgejo Actions:

```bash
./scripts/check-storage-policy.sh
./scripts/test-helm-chart.sh
./scripts/render-local-charts-for-kubeconform.sh
kubeconform -strict -summary -ignore-missing-schemas .forgejo-rendered
rumdl check --fix .
```

The render script recreates `.forgejo-rendered/`, which is ignored by Git. To
validate the Flux cluster resources separately:

```bash
kubectl kustomize --load-restrictor=LoadRestrictionsNone \
  kubernetes/flux/cluster
```

### Bootstrap or recover the cluster

A live deployment requires an existing Kubernetes cluster, access to the
Synology NFS export, a private Forgejo deploy key, and Infisical bootstrap
credentials. A full cluster rebuild also depends on Forgejo data being
available before Flux can fetch its source.

Follow [`docs/flux-gitops.md`](docs/flux-gitops.md) for the ordered bootstrap
procedure. It covers preparing external identity and secret material, installing
Flux Operator, creating the Flux SSH source Secret, applying the Flux instance,
and verifying reconciliation before changing any previous GitOps owner.

Do not put deploy keys, kubeconfig files, client secrets, or rendered Secrets
in Git. For data recovery and node loss, use
[`docs/backup-procedures.md`](docs/backup-procedures.md) and
[`docs/disaster-recovery.md`](docs/disaster-recovery.md).

### Add a service

1. Add or update `kubernetes/<service>/`.
2. Add its `HelmRelease` to the appropriate file in
   `kubernetes/flux/cluster/apps/`.
3. Add an external chart source to `kubernetes/flux/cluster/sources.yaml` when
   needed.
4. Add ingress, DNS, identity, and homepage configuration when applicable.
5. Store runtime credentials in Infisical and reference them from the chart.
6. Run the local validation commands before opening a change.

For persistent workloads, use `storageClassName: nfs-k8s`. Worker-local storage
is forbidden by the repository policy.

## Scope and known limits

This is a real homelab with explicit trade-offs. The current design still has
one control-plane node, one central NFS backend, single-replica services, and
some hardware-specific workloads. The runbooks document the resulting failure
modes and recovery steps.

## Further reading

- [`docs/architecture.md`](docs/architecture.md) explains the layers and
  reconciliation flow.
- [`docs/flux-gitops.md`](docs/flux-gitops.md) documents bootstrap, cutover, and
  rollback.
- [`docs/kubernetes-storage.md`](docs/kubernetes-storage.md) documents the NFS
  policy and PVC migration process.
- [`docs/backup-procedures.md`](docs/backup-procedures.md) and
  [`docs/disaster-recovery.md`](docs/disaster-recovery.md) cover recovery.
- [`docs/portfolio-summary.md`](docs/portfolio-summary.md) contains a concise
  CV-oriented project summary.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) lists contribution and validation rules.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
