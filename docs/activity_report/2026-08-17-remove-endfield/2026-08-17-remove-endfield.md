# Remove Endfield

## Problem

The Endfield scheduled Kubernetes workload was no longer wanted. Its local
Helm chart, rendered manifest, Flux `HelmRelease`, and active-chart index entry
needed to be removed so GitOps would stop managing it.

## Reasoning path and commands

First, locate every Endfield-named path:

```sh
rg --files -g '*endfield*' -g '*Endfield*' -g '*ENDFIELD*' .
find . -iname '*endfield*' -print
```

This found `kubernetes/endfield/`, `.forgejo-rendered/endfield.yaml`, and a
historical activity report. Repository-wide search then identified active
references in:

```text
kubernetes/flux/cluster/apps/applications.yaml
kubernetes/active-local-charts.txt
todo.md
```

The historical reports were retained as documentation. The active chart,
rendered manifest, Flux release, chart index entry, and TODO entry were removed.

The first deletion command was attempted with:

```sh
git rm -r -- kubernetes/endfield .forgejo-rendered/endfield.yaml
```

It failed because this environment exposes `.git/index` as read-only:

```text
fatal: Unable to create '/home/tmendy/Projects/homelab/.git/index.lock': Read-only file system
```

The already-verified paths were then removed directly:

```sh
rm -rf -- kubernetes/endfield .forgejo-rendered/endfield.yaml
```

## Checks and results

Search active configuration:

```sh
rg -n -i 'endfield' kubernetes .forgejo-rendered todo.md
```

Result: no active references were returned.

Check the live namespace:

```sh
kubectl get namespace endfield -o name
```

Result: unable to connect to `10.0.0.21:6443` because network access was not
available in this environment.

Run the repository storage-policy check:

```sh
./scripts/check-storage-policy.sh
```

Result:

```text
storage policy ok
```

## Final outcome

Endfield is no longer present in the repository's active Kubernetes GitOps
configuration. The next Flux reconciliation should remove the managed release
if the cluster is reachable. Live namespace deletion could not be verified from
this environment.
