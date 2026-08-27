# Update Navidrome and Newt images

## Problem

The image update checker reported newer compatible, digest-pinned images for
Navidrome and Newt. The repository values had to be updated without weakening
digest pinning.

## Reasoning and commands

The current values were inspected before editing:

```sh
sed -n '1,40p' kubernetes/navidrome/values.yaml
sed -n '1,45p' kubernetes/newt/values.yaml
```

The reported replacements were applied exactly:

```text
Navidrome: 0.63.2@sha256:9012939114fbb1bb641b81cf96dec5ded15f0aafefe8d47a511d7cb919658e40
Newt: 1.16.0@sha256:345fdeb369be6608d82c41d70637636c78b2c04a6112ff6ec20fc21c48afc899
```

No Kubernetes apply was performed. This repository is reconciled through Git,
so the changes must be reviewed and committed before the cluster receives
them.

## Validation

The following checks passed:

```sh
python3 scripts/test-check-image-updates.py
./scripts/test-helm-chart.sh
./scripts/render-local-charts-for-kubeconform.sh
./scripts/check-storage-policy.sh
git diff --check
```

The image update tests reported:

```text
Ran 4 tests in 0.001s
OK
```

The first attempt to query the cluster from the restricted environment failed:

```text
Unable to connect to the server: dial tcp 10.0.0.21:6443:
socket: operation not permitted
```

A read-only query then succeeded with the required network permission:

```sh
kubectl get pods -n navidrome -o wide
kubectl get pods -n newt-system -o wide
```

Both existing pods were healthy:

```text
navidrome: 1/1 Running, 0 restarts, node2
newt: 1/1 Running, 0 restarts, node3
```

The running image references were still the previous versions:

```text
deluan/navidrome:0.61.2@sha256:9fa40b3d8dec43ceb2213d1fa551da3dcfef6ac6d19c2e534efb92527c2bafd2
docker.io/fosrl/newt:1.12.5@sha256:3c009663332145cae39b940b07857469038d5e9d71aacb1497e78795ba4e3b9b
```

This confirms the workloads are currently running, but the new images have
not been deployed yet because the Git changes have not been reconciled.

## Final outcome

Updated:

- `kubernetes/navidrome/values.yaml` to Navidrome `0.63.2` with its exact
  digest.
- `kubernetes/newt/values.yaml` to Newt `1.16.0` with its exact digest.

The manifests render successfully and the current cluster pods are healthy.
After the change is committed and reconciled, check the pod image references
again and monitor rollout status.
