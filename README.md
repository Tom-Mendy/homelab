# Homelab platform

This repository contains the infrastructure code for a small Kubernetes platform
operated at home. It is a practical project used to learn and demonstrate
GitOps, platform engineering, DevSecOps, and recovery work.

The cluster runs applications from Git through Flux. Local Helm charts describe
the parts that need project-specific configuration. External services are
managed through pinned chart versions and reviewed Git changes.

## What this project demonstrates

- GitOps reconciliation with Flux and Helm releases.
- Kubernetes platform services for ingress, identity, secrets, storage, and
  observability.
- Application delivery through local Helm charts and Kustomize configuration.
- Secret delivery through Infisical instead of committed runtime credentials.
- Shared NFS-backed persistent storage that does not depend on one worker node.
- PostgreSQL workloads managed with CloudNativePG.
- CI checks for secrets, Helm rendering, Kubernetes schemas, Markdown, and the
  repository storage policy.
- Incident reports and recovery runbooks based on real maintenance work.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the public architecture
overview and [`docs/portfolio-summary.md`](docs/portfolio-summary.md) for the
short project description used on a CV.

- **Nodes**: `node1` (`10.0.0.21`), `node2` (`10.0.0.22`), `node3` (`10.0.0.23`)
- **Control plane**: `node1`
- **Workers**: `node2`, `node3`
- **Ingress**: Traefik
- **Storage**: Synology NFS (`10.0.0.11:/volume1/k8s`) through `nfs-k8s`
- **GitOps**: Flux Operator, Flux controllers, and native Flux resources
- **Git source**: the in-cluster Forgejo `homelab` repository

The public documentation uses example hostnames and network values. The live
cluster has environment-specific values and secrets that must not be copied
into a public repository.

## Repository layout

```text
homelab/
├── docs/                    # Operations and recovery runbooks
├── kubernetes/              # Application charts and Flux resources
├── navidrome/               # Local utility scripts
└── scripts/                 # Repository validation scripts
```

## GitOps bootstrap

The one-time bootstrap uses Helm and kubectl. It installs Flux Operator, creates
the private Forgejo pull Secret outside Git, and applies the `FluxInstance`.

Follow [`docs/flux-gitops.md`](docs/flux-gitops.md). Do not push the removal of
Argo CD Applications until Flux has been installed and Argo reconciliation has
been stopped as described in that runbook.

## Service onboarding

1. Add or update the chart under `kubernetes/<service>/`.
2. Add the corresponding `HelmRelease` to one of the application manifests
   under `kubernetes/flux/cluster/apps/`.
3. Add external chart sources to `kubernetes/flux/cluster/sources.yaml` when
   required.
4. Add DNS and homepage entries when the service has a user-facing endpoint.
5. Add native OIDC clients to the Authentik Blueprint and store each client
   secret under its own `/oidc/<client>` Infisical path.
6. Run the repository validation commands from the Flux runbook.

## Validation

The checks do not require access to the cluster:

```bash
./scripts/check-storage-policy.sh
./scripts/test-helm-chart.sh
./scripts/render-local-charts-for-kubeconform.sh
kubeconform -strict -summary -ignore-missing-schemas .forgejo-rendered
rumdl check README.md CONTRIBUTING.md SECURITY.md \
  docs/architecture.md docs/portfolio-summary.md docs/publication.md
```

The CI workflow also runs Gitleaks against the repository. Runtime secrets are
managed outside Git and injected by Infisical.

## Scope and limitations

This is an operational homelab, not a production-ready Kubernetes distribution.
The design still has accepted risks, including a single control plane, a
central NFS dependency, some single-replica services, and hardware-specific
workloads. Backup and restore work is documented separately and remains an
ongoing part of the project.

## Documentation

- [`docs/flux-gitops.md`](docs/flux-gitops.md)
- [`docs/network-diagram.md`](docs/network-diagram.md)
- [`docs/kubernetes-storage.md`](docs/kubernetes-storage.md)
- [`docs/backup-procedures.md`](docs/backup-procedures.md)
- [`docs/disaster-recovery.md`](docs/disaster-recovery.md)
- [`docs/portfolio-summary.md`](docs/portfolio-summary.md)

## License

The project is licensed under the Apache License 2.0. See [`LICENSE`](LICENSE).
