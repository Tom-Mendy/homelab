# Implement Coder agent workspaces

## Problem

The previous backlog proposed heavier virtual-machine and hosted-development
components for isolated agent work. The cluster instead needed a smaller
implementation that isolates each task, keeps persistent data available after
either worker fails, supports local inference, and provides one durable Hermes
assistant.

## Reasoning and commands

The implementation reuses the repository's Flux, CloudNativePG, Authentik,
Infisical, Traefik, Blocky, Homepage, and NFS patterns. Coder's official chart
already creates the service account permissions needed in selected workspace
namespaces, so no custom RBAC chart was added.

The official chart URL was verified from its repository index. Two failed
lookups identified the correct archive naming convention:

```console
$ helm show values oci://ghcr.io/coder/coder/coder --version 2.35.3
Error: failed to perform "FetchReference" ... not found

$ helm show values https://helm.coder.com/v2/coder-2.35.3.tgz
Error: failed to fetch ... 404 Not Found

$ curl -fsSL https://helm.coder.com/v2/index.yaml
...
urls:
- https://helm.coder.com/v2/coder_helm_2.35.3.tgz
version: 2.35.3

$ helm show values https://helm.coder.com/v2/coder_helm_2.35.3.tgz
coder:
  env: []
  serviceAccount:
    workspaceNamespaces: []
```

The official Coder Deployment template was then used as the minimal base. The
workload image digests and Hermes release tag were resolved before pinning:

```console
$ docker buildx imagetools inspect codercom/example-universal:ubuntu \
    --format '{{json .Manifest}}'
"digest": "sha256:411973a25007c309162e36958038ccf0f93d7cb48bf295f3da16bd30658c3ca7"

$ curl -fsSL \
'https://api.github.com/repos/NousResearch/hermes-agent/releases?per_page=30' \
    | jq -r '.[] | select(.name | test("v0\\.18\\.0")) | [.tag_name,.name] | @tsv'
v2026.7.1 Hermes Agent v0.18.0 (2026.7.1) — The Judgment Release

$ docker buildx imagetools inspect nousresearch/hermes-agent:v2026.7.1 \
    --format '{{json .Manifest}}'
"digest": "sha256:b6c019227889e6675424a2b6223b2cafdd36bf7d1048d1ddd8e043b880d6cc0f"
```

OpenAI documentation confirmed that local Codex clients can use `codex login`
with ChatGPT subscription access. Hermes documentation additionally confirmed
its native `openai-codex` device-code flow. Coder Agents remains configured
against the existing Ollama OpenAI-compatible endpoint so no subscription
credential is stored centrally or injected into task workspaces.

## Changes

- Added Coder 2.35.3 through its official Helm repository.
- Added a CloudNativePG 17 database with a 10 GiB `nfs-k8s` volume.
- Added Authentik OIDC, Infisical secret delivery, Traefik ingress, Blocky DNS,
  and Homepage discovery.
- Added `coder-workspaces` quota and defaults sized for one Hermes and two
  standard workspaces.
- Added two pinned Terraform templates. Both use Kubernetes Deployments and
  `nfs-k8s` PVCs, allowing rescheduling between workers.
- Added the operator runbook for Coder Agents, Forgejo SSH, Hermes OAuth,
  Hindsight local mode, template publication, and worker-failure checks.

## Validation results

The first Terraform formatting check found both new files and exited `3`:

```console
$ terraform fmt -check -recursive kubernetes/coder/workspace-templates
kubernetes/coder/workspace-templates/agent-workspace/main.tf
kubernetes/coder/workspace-templates/hermes-personal/main.tf
```

After `terraform fmt`, both isolated provider validations passed:

```console
$ terraform validate
Success! The configuration is valid.
```

The sandbox initially prevented the downloaded providers from starting. The
same read-only validation outside that execution restriction succeeded, which
showed that the failure was environmental rather than a template error.

Helm and storage checks passed:

```console
$ helm lint kubernetes/coder
1 chart(s) linted, 0 chart(s) failed

$ helm lint kubernetes/authentik
1 chart(s) linted, 0 chart(s) failed

$ ./scripts/check-storage-policy.sh
storage policy ok
```

The repository-wide chart test initially failed on the stale `openwebui` entry
in `active-local-charts.txt`; that chart no longer exists as a local chart. The
entry was removed and the complete test then passed for all 23 active charts:

```console
$ ./scripts/test-helm-chart.sh
=== coder ===
OK
...
=== vaultwarden ===
OK
```

The first built-in Kustomize command hit its known load restriction because
the repository intentionally loads values from outside `flux/cluster/apps`:

```console
$ kubectl kustomize kubernetes/flux/cluster
error: ... values.yaml ... is not in or below ... flux/cluster/apps

$ kubectl kustomize kubernetes/flux/cluster \
    --load-restrictor LoadRestrictionsNone
# rendered successfully
```

The official Coder chart, local charts, and full Flux output were validated as
one set:

```console
$ kubeconform -strict -ignore-missing-schemas -summary \
    /tmp/coder-official.yaml /tmp/coder-extras.yaml \
    /tmp/authentik-extras.yaml /tmp/coder-flux.yaml
Summary: 85 resources found in 4 files - Valid: 31, Invalid: 0, \
Errors: 0, Skipped: 54
```

The first final `kubeconform` retry could not access the Nix daemon socket from
the sandbox. Running the identical validation with daemon access produced the
successful summary above.

`rumdl check --fix .` also exposed pre-existing Markdown line-length issues
outside this change. Its automatic unrelated edits were reverted. The two new
documents pass independently:

```console
$ rumdl check kubernetes/coder/README.md \
    docs/activity_report/2026-08-17-agentic-workspaces-coder/\
2026-08-17-agentic-workspaces-coder.md
Success: No issues found in 2 files
```

## Final outcome

The repository now declares the complete GitOps platform and workspace
templates. Flux reconciliation, Infisical secret creation, one-time Coder
database configuration, template publication, and live node-drain tests remain
explicit operator actions because they change the running cluster or external
identity state.
