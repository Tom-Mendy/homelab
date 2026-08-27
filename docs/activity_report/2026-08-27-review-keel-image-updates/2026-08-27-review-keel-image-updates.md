# Review Keel and image update practices

## Problem

The cluster had two rules that appeared to conflict:

- update applications often enough to receive fixes;
- pin container images to an exact digest so their content cannot change
  without a Git change.

Keel was also allowed to update many live workloads while Flux managed those
same workloads from Git with drift correction enabled. The review had to decide
which controller should own image changes and how regular upgrades should work.

## Investigation and reasoning

The repository configuration was checked first:

```sh
rg -n 'keel\.sh/(policy|trigger|matchTag)' kubernetes
sed -n '1,90p' kubernetes/keel/values.yaml
sed -n '500,555p' kubernetes/flux/cluster/apps/applications.yaml
rg -n 'kind: (ImageRepository|ImagePolicy|ImageUpdateAutomation)' kubernetes
sed -n '1,240p' .forgejo/workflows/homelab-validation.yml
```

Results:

```text
21 workload definitions contain keel.sh/policy annotations
most policies: all
blocky and traefik policies: minor
keel default policy: patch
keel Helm provider: disabled
keel HelmRelease chart version: 1.2.0
Flux HelmRelease drift detection: enabled
Flux image automation resources: no matches
```

The Forgejo workflow runs Gitleaks, local Helm rendering, kubeconform, and the
storage-policy check. It has no runtime application or ingress smoke tests. That
means a dependency pull request can be checked for syntax and policy, but should
not be auto-merged on the assumption that the application works.

Read-only cluster queries were then used to compare Git with the live state. The
first attempt failed because the execution sandbox blocked the Kubernetes API:

```sh
kubectl config current-context
kubectl get gitrepository -A
```

Result:

```text
kubernetes-admin@cluster.local
Unable to connect to the server: dial tcp 10.0.0.21:6443:
socket: operation not permitted
```

The same read-only checks were rerun with approved network access:

```sh
kubectl get gitrepository -A
kubectl get helmrelease -A
kubectl get deployment -A -o json | jq -r '
  .items[]
  | select(.spec.template.metadata.annotations
      | to_entries[]?
      | .key | startswith("keel.sh/"))
  | [.metadata.namespace, .metadata.name,
     (.spec.template.spec.containers | map(.image) | join(","))]
  | @tsv'
kubectl get crd | rg 'image(repositor|polic|updateautomation)'
kubectl get pods -n keel -o wide
kubectl get deployment -n keel keel -o json | jq -r '
  .spec.template.spec.containers[]
  | .image, (.env[]? | select(.name == "POLL" or
      .name == "POLL_DEFAULTSCHEDULE") | "\(.name)=\(.value)")'
kubectl get helmrelease -n flux-system keel -o json | jq -r '
  .status.conditions[] | [.type, .status, .reason, .message] | @tsv'
```

Observed results:

```text
Git source revision: refs/heads/main@sha1:fa61596ee693...
Git source status: Ready
Keel HelmRelease: Ready
Keel extras HelmRelease: Ready
Keel pod: Running on node2
Keel image: ghcr.io/keel-hq/keel:0.21.1
POLL=true
POLL_DEFAULTSCHEDULE=@every 1m
Keel HelmRelease drift condition: no drift detected
Flux image automation CRDs: no matches
```

The live Deployments reflected the same Keel annotations found in Git. Their
image references included a mixture of exact `tag@sha256` pins and tag-only
references.

The controller behavior was then compared with upstream documentation and
source:

- Kubernetes uses a digest, rather than the tag, when both appear in an image
  reference. Tags can move; digests do not.
- Keel updates live workload specs. Its documented same-tag mode intentionally
  follows mutable tag content.
- The inspected Keel Kubernetes provider update path constructs the replacement
  from the image repository and tag, without retaining an existing digest.
- Flux Helm drift correction restores fields that differ from Git.
- Renovate supports Forgejo, Docker digest pins, Helm values, Flux release
  definitions, and custom regex matching.
- Flux image automation records image changes in Git and is suitable for a
  narrower set of first-party images.

This led to one ownership rule: Git records the exact desired image, and Flux is
the only controller that writes that desired state to the cluster. An updater
may propose or commit a new pin in Git, but it should not bypass Git by editing
a Flux-managed Deployment.

## Changes made

Added the English guidance document:

```text
docs/update-guidance.md
```

It records:

- why regular updates and digest pinning are compatible;
- the current Keel and Flux conflict;
- a comparison of Keel, Renovate, and Flux image automation;
- update rules for platform, stateful, stateless, and first-party workloads;
- a daily detection, weekly triage, and maintenance-window review cadence;
- rollout, rollback, and security practices;
- a staged migration from Keel to Renovate pull requests.

No Kubernetes manifest, controller, secret, workload, or live cluster object was
changed during this review.

## Validation

The documentation change was checked with:

```sh
rumdl check --fix docs/update-guidance.md \
  docs/activity_report/2026-08-27-review-keel-image-updates/2026-08-27-review-keel-image-updates.md
./scripts/check-storage-policy.sh
rg -n --glob '*.yaml' --glob '*.yml' 'local-path' kubernetes
git diff --check
```

Results:

```text
rumdl: Success, no issues found in 2 files
storage policy ok
local-path search: no matches
git diff --check: no output
```

## Outcome

The apparent contradiction is resolved by treating a pin as the exact current
state, not as a promise to remain on one version forever. Renovate should open a
pull request that moves the tag and digest together. After review and merge,
Flux deploys the new pin.

Keel should be removed from Flux-managed workloads in stages. Auto-merge should
remain disabled until the repository has application-level smoke tests. Flux
image automation remains an option for selected images built by this homelab,
provided it records each update in Git.
