# Image update guidance for this cluster

## Decision

Keep application images pinned in Git by tag and digest. Use an updater to
propose a new pin in Git, then let Flux deploy the merged change.

Keel has been removed from this cluster. Renovate in pull-request-only mode is
the best general update tool for this repository. It can update container
images, image digests, Helm values, and Flux `HelmRelease` chart versions. Flux
remains the only component that changes workloads in the cluster.

Do not add another live updater that edits workloads managed by Flux. Keep
updates in Git and let Flux reconcile the merged state.

The intended path is:

```text
Registry release
      |
      v
Renovate pull request with a new tag and digest
      |
      v
Forgejo validation and human review
      |
      v
Merge to main
      |
      v
Flux reconciliation and rollout verification
```

## Pinning and regular updates are compatible

Pinning answers, "What exact bytes should run now?" Updating answers, "How do
we choose and record the next exact bytes?"

A mutable tag such as `latest` or even `1.2.3` can point to different content
later. A digest identifies one image manifest. Kubernetes uses the digest when
an image reference contains both a tag and digest, so this form is readable and
reproducible:

```yaml
image: ghcr.io/example/application:1.2.3@sha256:0123456789abcdef...
```

The pin should move regularly, but only through a reviewed Git change. This
gives every upgrade a diff, CI result, author, date, and simple rollback commit.
It also prevents a pod restart from silently selecting different image content.

`imagePullPolicy: Always` does not provide updates. It makes the kubelet resolve
the image reference whenever a container starts. A digest still resolves to the
same content. The policy does not watch registries or edit workload specs.

See the Kubernetes documentation on [image names, tags, and digests](https://kubernetes.io/docs/concepts/containers/images/).

## What was running before removal

Before this change, the repository had the following update model:

- Flux reads `main` from the in-cluster Forgejo repository and reconciles the
  cluster.
- Flux Helm releases enable drift detection and correction.
- Keel is installed from chart `1.2.0`. The live pod uses
  `ghcr.io/keel-hq/keel:0.21.1`, polling every minute.
- The Keel Helm provider is disabled.
- Twenty-one workload definitions carry `keel.sh/policy` annotations. Most use
  `all`; Blocky and Traefik use `minor`.
- Many image references already use `tag@sha256`, although some tag-only images
  remain.
- No Flux `ImageRepository`, `ImagePolicy`, or `ImageUpdateAutomation` resources
  are installed.
- Forgejo validates secrets, local Helm charts, rendered Kubernetes resources,
  and the storage policy. It does not run application smoke tests.

That left two controllers with different desired states. Keel edited a live
Deployment when it finds an update. Git still contains the old image, and Flux
then sees Keel's edit as drift. With drift correction enabled, Flux can restore
the Git-pinned image. The exact timing depends on reconciliation, but the design
is inherently unstable.

There is a second problem. Keel's Kubernetes provider builds an updated image
reference from the repository and tag. In the provider code inspected during
this review, that update path does not preserve an existing digest. A successful
Keel update can therefore replace `tag@sha256` with `tag`. Even if Flux did not
revert the change, the live state would no longer be pinned to the reviewed
digest.

Flux documents this reconciliation behavior in
[HelmRelease drift detection](https://fluxcd.io/flux/components/helm/helmreleases/#drift-detection).

Keel documents a same-tag mode for mutable tags using `policy: force`,
`keel.sh/matchTag: "true"`, polling, and `imagePullPolicy: Always`. That solves
a different problem. It deliberately follows mutable content and is a poor fit
for this GitOps repository. See [Keel's policy documentation](https://keel.sh/docs/)
and the inspected [Kubernetes provider update path](https://github.com/keel-hq/keel/blob/v0.20.1-beta.1/provider/kubernetes/updates.go#L770-L780).

## Tool choice

| Tool | Where it changes state | Audit and rollback | Fit here |
| --- | --- | --- | --- |
| Keel | Live Kubernetes objects | Change is absent from Git and Flux may revert it | Removed from this cluster |
| Flux image automation | Commits image changes to Git | Strong Git audit trail | Good for selected first-party images that need fast delivery |
| Renovate | Opens pull requests or commits in Git | Strong review and rollback path | Best default for images and Helm charts |

Renovate supports Forgejo and understands conventional Helm values such as
`image.repository` plus `image.tag`. It can pin and refresh Docker digests. Its
Flux manager can also update `HelmRelease` chart versions, but this repository
needs explicit file matching because its Flux files do not use the manager's
default path. Some releases also omit `metadata.namespace` because a parent
Kustomization supplies it. Confirm or fix those source namespaces during the
pilot instead of assuming Renovate detected every release.

Full image strings inside custom charts may need a Renovate regex manager with
`currentDigest` support. Start with conventional values files, inspect the first
set of pull requests, then add custom matching for the remaining image fields.
The official references are [Renovate's Forgejo platform support](https://docs.renovatebot.com/modules/platform/forgejo/),
[Docker digest pinning](https://docs.renovatebot.com/docker/),
[Helm values support](https://docs.renovatebot.com/modules/manager/helm-values/),
[Flux support](https://docs.renovatebot.com/modules/manager/flux/), and
[regex managers](https://docs.renovatebot.com/modules/manager/regex/).

Flux image automation is still useful for images built by this homelab. It also
writes the selected image to Git before Flux deploys it. Prefer immutable CI
tags, for example a version or commit SHA, over repeatedly publishing one tag.
Mutable-tag tracking is possible with digest reflection, but it hides the source
version behind a changing digest and makes release history harder to read. See
the [Flux image update guide](https://fluxcd.io/flux/guides/image-update/) and
[image automation API](https://fluxcd.io/flux/components/image/imageupdateautomations/).

## Update rules by workload

| Workload class | Examples in this cluster | Update rule |
| --- | --- | --- |
| Recovery and platform services | Flux, Forgejo, Traefik, Blocky, NFS provisioner, Infisical, Authentik, CloudNativePG, monitoring | Reviewed pull request. Read release notes and verify recovery access before merging. |
| Stateful applications | Vaultwarden, Atuin, Matrix, media applications, Navidrome, Trilium, Coder | Reviewed pull request. Confirm a current backup, read migration notes, and check the rollout and data after deployment. |
| Lower-risk stateless applications | Homepage, Stirling PDF, similar replaceable services | Pull request first. Consider patch-only auto-merge later, after adding useful smoke tests. |
| Images built by this repository | NymVPN sidecars or workspace images | Renovate or optional Flux image automation. Publish immutable CI tags and commit every selected version to Git. |

These rules apply separately to container images and Helm chart versions. A new
chart can change templates, defaults, RBAC, or storage independently of the
application image. Keep chart versions exact and review chart release notes.

Do not auto-merge updates yet. Current CI catches malformed manifests and
storage-policy violations, but it cannot tell whether Vaultwarden starts, a
database migration succeeds, or an ingress still serves traffic. Human review
is the missing safety check. If runtime smoke tests are added later, begin with
patch updates for lower-risk stateless applications and use a minimum release
age. Renovate's [upgrade best practices](https://docs.renovatebot.com/upgrade-best-practices/)
recommend waiting at least 14 days before auto-merging third-party releases.

Major updates stay manual. Minor updates should also stay manual for platform
and stateful workloads. Security updates may justify a faster review, but should
still produce a Git change.

## Suggested operating cadence

Run Renovate every day so new releases appear promptly, but review them on a
schedule that matches the workload:

- Triage the dependency dashboard and security updates each week.
- Merge low-risk patch updates during a weekly maintenance window.
- Handle platform and stateful updates in a monthly window with a backup and
  enough time to watch the rollout.
- Review a critical, remotely exploitable vulnerability as soon as it is
  reported. Faster review does not mean bypassing Git or skipping rollback
  preparation.

Avoid one pull request that upgrades several unrelated stateful services. A
smaller change is easier to diagnose and revert. Digest-only refreshes for a
mutable upstream tag also need review because the content changed even when the
tag did not.

## When Keel can still make sense

Keel is reasonable when it is the only owner of a disposable workload and the
operator accepts direct in-cluster updates. Examples include a short-lived test
environment or a cluster that does not reconcile workload images from Git.

That is not this cluster. Keeping Keel would require giving it ownership of the
image field and teaching Flux to ignore that drift. The deployed image would
then stop matching the repository, which removes the audit and rollback
properties this GitOps setup was built to provide.

## Rollout and rollback

Before merging an application update:

1. Read the upstream changelog and check for database, configuration, and chart
   migrations.
2. Confirm that stateful data has a recent usable backup.
3. Check the proposed tag and digest. The tag helps humans; the digest fixes the
   exact artifact.
4. Review rendered manifest changes and all Forgejo checks.

After Flux deploys it:

```sh
flux get helmreleases -A
kubectl get pods -A
kubectl rollout status deployment/<name> -n <namespace>
kubectl logs deployment/<name> -n <namespace> --since=10m
```

Use an application-specific health request or login test where possible. A
Running pod only proves that the process has not exited.

For rollback, revert the update commit or merge a pull request restoring the
previous tag and digest. Let Flux apply that Git state. If the release performed
an irreversible data migration, restore the documented backup instead of
assuming an older container can read the new data.

## Next steps after removal

1. Deploy Renovate against Forgejo in pull-request-only mode. Limit the first
   run to a few conventional Helm values files and set dependency concurrency
   low enough to keep reviews readable.
2. Enable digest pinning and verify that a pull request updates both the tag and
   digest where appropriate.
3. Configure Renovate's Flux file matching for `kubernetes/flux/cluster/`.
   Address missing release or source namespaces where the Flux manager requires
   them.
4. Add custom regex managers for full-string image fields that the Helm values
   manager does not detect. Test each expression against this repository before
   widening it.
5. Consider Flux image automation later for a small set of first-party images.
   Keep its commits visible in the same Git history.

The Keel removal is recorded in the repository and must be merged before Flux
prunes the live releases. Renovate installation remains a separate change.

## Security boundary

A digest proves image identity, not trust. It does not show that the publisher
is legitimate or that the image is free of vulnerabilities. Keep secret
scanning in CI, add image vulnerability scanning where practical, and consider
signature verification for high-impact services. Those controls complement
pinning; they do not replace it.
