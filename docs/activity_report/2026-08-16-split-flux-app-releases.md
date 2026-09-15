# Split Flux application releases

## Problem

`kubernetes/flux/cluster/apps/releases.yaml` had grown to 937 lines and
contained every Flux `HelmRelease`, making it difficult to navigate and review.

## Reasoning and commands

The resource definitions do not need to change to split the file. Kustomize
can load multiple files from the same directory, so the releases were grouped
by role while preserving every manifest:

- `platform.yaml` for cluster platform services.
- `identity.yaml` for authentik and Infisical services.
- `applications.yaml` for user-facing applications.
- `runners.yaml` for ARC and Forgejo runners.

```sh
kubectl kustomize kubernetes/flux/cluster/apps \
  --load-restrictor LoadRestrictionsNone
```

The rendered output is used to confirm that the split manifests remain valid
as a single Flux application set.

## Outcome

The monolithic `releases.yaml` was removed. `kustomization.yaml` now lists the
four smaller files, without changing HelmRelease names, values, dependencies,
or namespaces.
