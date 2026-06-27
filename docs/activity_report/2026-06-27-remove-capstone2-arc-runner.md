# Remove Capstone2 ARC Runner

## Problem

The `arc-runner-set-capstone2` listener pods in `arc-systems` were repeatedly
cycling through `Error`, `Terminating`, and `ContainerCreating`. The requested
fix was to remove that runner scale set.

## Reasoning and Commands

Find the repo and live cluster references:

```sh
rg -n "capstone2|Capstone2|arc-runner-set-capstone2" kubernetes docs README.md
kubectl get app -n argocd | rg 'capstone2|runner|actions'
kubectl get all -A | rg 'capstone2|arc-runner-set'
```

The runner was managed by one Argo CD app:

```text
kubernetes/argocd/apps/github-runners-capstone2.yaml
```

That app referenced one values file:

```text
kubernetes/github-runners/runner-scale-set-capstone2-values.yaml
```

The ARC controller and other runner scale sets were separate resources, so they
did not need to be removed.

## Changes

Deleted the Capstone2 Argo CD app manifest:

```text
kubernetes/argocd/apps/github-runners-capstone2.yaml
```

Deleted the Capstone2 runner values file:

```text
kubernetes/github-runners/runner-scale-set-capstone2-values.yaml
```

Removed current documentation references from:

```text
README.md
docs/argocd-gitops.md
kubernetes/github-runners/README.md
```

Deleted the live child Argo CD app after the root `homelab` app synced the Git
change:

```sh
kubectl annotate app -n argocd homelab argocd.argoproj.io/refresh=hard --overwrite
kubectl delete app -n argocd github-runners-capstone2 --ignore-not-found=true
```

The Argo CD app deletion left ARC custom resources behind, so the scale set was
deleted directly:

```sh
kubectl delete autoscalingrunnerset -n arc-runners arc-runner-set-capstone2 --ignore-not-found=true
```

One orphaned listener remained after the scale set delete, so it was removed
directly:

```sh
kubectl delete autoscalinglistener -n arc-systems arc-runner-set-capstone2-c8655b54-listener --ignore-not-found=true
```

## Verification

Check for active current references:

```sh
rg -n "capstone2|Capstone2|arc-runner-set-capstone2" README.md docs kubernetes
```

Only historical activity-report references should remain.

Run the storage policy check even though this change does not add storage:

```sh
./scripts/check-storage-policy.sh
```

## Outcome

The repository no longer defines `github-runners-capstone2` or
`arc-runner-set-capstone2`. The root `homelab` Argo CD app is synced to the
removal commit, and the live Capstone2 ARC custom resources were removed.
