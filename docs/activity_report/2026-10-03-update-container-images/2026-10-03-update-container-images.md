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
passed. Flux initially failed the Ollama Helm upgrade because an old,
completed function-sync Job had an immutable pod template. Updated its
deterministic name checksum to include the image configuration and
removed the changing chart-version label from its immutable pod template.
After removing the old completed Job, Flux then reported the Ollama release
ready and the new function-sync Job completed successfully.

The PostgreSQL primary restarted onto 18.6 and recovered to a healthy
CNPG cluster. The new Newt pod connected to Pangolin, the Ollama pod is
ready on 0.35.1, and all four Forgejo runner deployments became ready
with the updated Docker-in-Docker digest. The Harbor configuration
post-upgrade hook succeeded with the Python image. The AWS CLI backup
CronJob template now references 2.37.9; its next scheduled execution has
not occurred yet.

The Wakapi chart values are updated to 2.18.1, but no Wakapi workload or
Flux HelmRelease exists in the live cluster, so there was no runtime
rollout to verify for it.

The NZBGet rollout could not complete: its replacement pod landed on
node2, where the unchanged NymVPN init sidecar repeatedly failed its
startup probe and was killed. The old NZBGet pod remained ready. Reverted
only the NZBGet image to its previous known-good pin to avoid interrupting
service; investigate the node2 NymVPN startup issue separately.

After that rollback, the image checker reports NZBGet as outdated and
the same 5 registry errors. The other 7 image updates remain deployed
through Flux on Forgejo `main`.

## Outcome

Forgejo `main` revision `78a09f4` is applied and the Flux Kustomization is
Ready. All applicable changed HelmReleases are Ready; the only Pending
pod observed is the pre-existing `poc-s3-queue-worker/nats-0` (14 days
old). The final image scan has 34 current references, one outdated
NZBGet reference, and five registry errors. NZBGet stays on its previous
pin pending investigation of the node2 VPN sidecar startup.
