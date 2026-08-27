# Remove Keel from the cluster configuration

## Problem

Keel edited live Kubernetes workloads while Flux reconciled the same workloads
from Git. That created two owners for image updates. Keel could also remove a
digest from an image reference, while this repository pins images to exact
`tag@sha256` values.

The previous review concluded that Keel was not useful in this Flux-managed
cluster. This activity removed its active configuration and supporting
references.

## Reasoning and commands

The complete active footprint was found before editing:

```sh
rg -n -i 'keel' kubernetes docs .forgejo \
  --glob '!docs/images/**' \
  --glob '!docs/activity_report/**' \
  --glob '!docs/hermes/**'
rg --files kubernetes | rg '(^|/)(keel|.*keel.*)' | sort
```

The search found:

- two Flux `HelmRelease` objects;
- one Flux `HelmRepository`;
- one generated Keel values ConfigMap;
- the local Keel extras chart;
- `keel.sh/*` annotations on application workloads;
- Homepage, Blocky DNS, ACME, backup, and README references.

Historical activity reports were excluded from the active search and were kept
unchanged.

The GitOps rollout was chosen deliberately. Flux reads `main`, so the safe
sequence is to merge the repository deletion first, let Flux uninstall the
Helm releases, then check the namespace before deleting it if it is empty. A
direct deletion before the Git change could be recreated by Flux.

## Changes made

- Removed the Keel and Keel extras `HelmRelease` objects.
- Removed the Keel Helm repository and generated values ConfigMap.
- Deleted the local Keel chart and removed it from the local chart test list.
- Removed all active `keel.sh/*` annotations from workloads.
- Removed the Keel Homepage entry, Blocky DNS record, ACME check, backup entry,
  README image, and dashboard image.
- Updated `docs/update-guidance.md` to record Keel as removed and to describe
  Renovate plus Flux as the future update path.

Pinned image references were not changed. External Infisical data was not
deleted. The Infisical resources owned by the Keel Helm release will be removed
when Flux uninstalls that release.

## Validation

The following checks were run after the edits:

```sh
./scripts/test-helm-chart.sh
./scripts/render-local-charts-for-kubeconform.sh
./scripts/check-storage-policy.sh
rumdl check --fix docs/update-guidance.md \
  docs/activity_report/2026-08-27-remove-keel/2026-08-27-remove-keel.md
git diff --check
```

The active configuration search was also repeated:

```sh
rg -n -i 'keel|keel\.sh' kubernetes README.md \
  docs/acme-dns01-private-services.md docs/backup-procedures.md
```

Results:

```text
./scripts/test-helm-chart.sh: all 25 local charts passed
./scripts/render-local-charts-for-kubeconform.sh: completed successfully
storage policy ok
rumdl: Success, no issues found in 2 files
active Keel reference search: no matches
git diff --check produces no output
```

The first Flux render attempt used the default Kustomize load restriction and
failed because the repository's values files are outside the application
Kustomization directory:

```sh
kubectl kustomize kubernetes/flux/cluster
```

The error reported that `kubernetes/github-runners/controller/values.yaml` was
not below `kubernetes/flux/cluster/apps`. The repository's Kustomization needs
these cross-directory files, so the render was repeated with the explicit
restriction override:

```sh
kubectl kustomize \
  --load-restrictor LoadRestrictionsNone \
  kubernetes/flux/cluster \
  >/tmp/homelab-flux-render.yaml
rg -n -i 'keel|keel\.sh' /tmp/homelab-flux-render.yaml
```

That render succeeded and the rendered Flux resources contained no Keel
references. A `flux build kustomization` attempt could not inspect the live
Kubernetes API from the restricted execution environment, so it was not used
as the render result.

The live namespace must be checked after the change is merged and reconciled:

```sh
flux get helmreleases -A
kubectl get all,cm,secret,ing -n keel
kubectl get namespace keel
```

The read-only check before the Git change reached `main` showed the expected
transition state:

```text
flux-system  keel         True
  Helm upgrade succeeded for release keel/keel.v2 with chart keel@1.2.0
flux-system  keel-extras  True
  Helm upgrade succeeded for release keel/keel-extras.v79 with chart
  keel-local-extras@0.1.0+b7ea5c87110c
keel pod: Running on node2
keel namespace: Active
Flux source: refs/heads/main@sha1:b7ea5c87, Ready
```

The local deletion is therefore ready for the normal Git merge and Flux prune
sequence. The live resources were not deleted directly during this activity.

If the namespace has no remaining resources, delete the Helm-created namespace
manually. It is not declared in `kubernetes/flux/cluster/namespaces.yaml`.

## Outcome

Keel is no longer declared or used by the repository. Flux remains the only
component that applies application state. The live Keel resources will be
pruned when this Git change reaches the Flux source on `main`.
