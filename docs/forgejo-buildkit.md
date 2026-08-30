# Forgejo BuildKit runner

Forgejo image workflows use the `buildkit` runner label and publish to the
private Harbor project `homelab`. The runner keeps DinD only as Forgejo's job
container backend; image builds run with rootless BuildKit and do not use the
Docker socket.

The BuildKit job container receives `/dev/fuse` and uses `fuse-overlayfs` for
its rootless snapshotter. Keep the device mapping together with the unconfined
seccomp, AppArmor, and system-path profiles in the BuildKit runner values.
Without the device, BuildKit falls back to the `native` snapshotter and copies
the complete root filesystem for every image layer.

Daemonless builds also use `--oci-worker-no-process-sandbox`. A nested
rootless worker cannot mount a separate `/proc` filesystem inside the job
container; the Forgejo job container remains the outer isolation boundary.

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

The bootstrap workflow builds and publishes an immutable commit-tagged image.
It disables Docker's default OCI provenance attachment because Harbor currently
returns HTTP 412 when indexing that attachment for this image:

```text
harbor.home.tom-mendy.com/homelab/ci/buildkit-forgejo
```

## Image policy

Application workflows publish an immutable commit tag, their release tag,
`latest`, and a registry-backed `buildcache` tag. The bootstrap image is
published only with its commit tag because Harbor may reject overwriting a
mutable tag while an attestation is being indexed. Kubernetes references should
be updated to the resulting Harbor digest after a release build.

The local `homelab` project scans images and generates SBOMs automatically, but
does not enable Harbor's `prevent_vul` pull gate. Harbor applies that gate to
manifest `HEAD` requests, so a vulnerable image already in the registry cannot
be replaced by a rebuilt image. Treat High and Critical findings as CI and
remediation signals, and deploy immutable digests. Proxy-cache projects retain
the pull gate.

## Rollback

Keep the existing `ubuntu-latest` workflows until a BuildKit run has completed.
If the BuildKit runner is unavailable, restore the workflow's `runs-on` value to
`ubuntu-latest` and re-enable the previous Forgejo Registry push step.
