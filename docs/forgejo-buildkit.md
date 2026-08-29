# Forgejo BuildKit runner

Forgejo image workflows use the `buildkit` runner label and publish to the
private Harbor project `homelab`. The runner keeps DinD only as Forgejo's job
container backend; image builds run with rootless BuildKit and do not use the
Docker socket.

## One-time prerequisites

Create a Harbor robot account scoped to project `homelab` with artifact pull
and push permissions. Store its credentials in both locations:

- Forgejo repository secrets: `HARBOR_REGISTRY_USER` and
  `HARBOR_REGISTRY_TOKEN`.
- Infisical `/harbor/ci`: `HARBOR_CI_USERNAME` and `HARBOR_CI_TOKEN`.

The Infisical identity configured in
`kubernetes/forgejo-runner/buildkit/values.yaml` must be allowed to read
`/harbor/ci`. Replace the identity placeholder and the BuildKit runner image
digest after the bootstrap workflow publishes the image. Then remove
`spec.suspend: true` from the `forgejo-runner-buildkit` HelmRelease.

The bootstrap workflow builds and publishes:

```text
harbor.home.tom-mendy.com/homelab/ci/buildkit-forgejo
```

## Image policy

Application workflows publish an immutable commit tag, their release tag,
`latest`, and a registry-backed `buildcache` tag. Kubernetes references should
be updated to the resulting Harbor digest after a release build.

## Rollback

Keep the existing `ubuntu-latest` workflows until a BuildKit run has completed.
If the BuildKit runner is unavailable, restore the workflow's `runs-on` value to
`ubuntu-latest` and re-enable the previous Forgejo Registry push step.
