# Update Kubernetes container images

## Problem

Check current container image references in the homelab GitOps
repository and update compatible releases without bypassing Flux. The
local checkout had diverged from Forgejo `main`; the cluster was
reconciling Forgejo `main` at `7bceb655`.

## Reasoning and commands

Used a separate worktree based on the cluster's exact Forgejo
`origin/main` revision, leaving the divergent local branch untouched:

```sh
git worktree add -b maintenance/container-image-updates \
  /opt/data/cache/scratch/homelab-image-updates origin/main
python3 scripts/test-check-image-updates.py -v
python3 scripts/check-image-updates.py --json
```

The checker found 8 outdated image references, 27 current references,
and 5 registry errors in the unmodified baseline. The errors were
private Harbor repositories that denied anonymous pulls and a
`sumfeet-actions-runner:latest` image reference returning 404. Those
references were not changed.

Reviewed the candidate tags and release context. PostgreSQL stays on
major version 18 (18.4 to 18.6); its 18.6 release notes describe fixes,
with no major-version data migration involved. The latest PostgreSQL
backup CronJob completed successfully on 2026-10-03T00:30:04Z. The
backup PVC was Bound on `nfs-k8s`, and the CNPG cluster was healthy
before deployment.

Updated only pinned image tag/digest values in:

- `kubernetes/newt/values.yaml`
- `kubernetes/forgejo-runner/values.yaml`
- `kubernetes/job-search-manager/values.yaml` (PostgreSQL 18 and AWS CLI
  backup images)
- `kubernetes/wakapi/values.yaml`
- `kubernetes/media/values.yaml` (NZBGet)
- `kubernetes/ollama/values.yaml`
- `kubernetes/harbor-config/values.yaml` (Python)

Validated with:

```sh
./scripts/test-helm-chart.sh
./scripts/check-storage-policy.sh
python3 scripts/test-check-image-updates.py -v
python3 scripts/check-image-updates.py --json
```

The Helm chart tests and storage policy passed; all 5 checker unit tests
passed. A post-edit image scan found 35 current references, no outdated
references, and the same 5 registry errors. Rendered updates were
prepared for Flux deployment from Forgejo `main`.

## Outcome

The candidate image references were updated in GitOps source. Cluster
rollout and application health checks are recorded after the Forgejo
`main` deployment.
