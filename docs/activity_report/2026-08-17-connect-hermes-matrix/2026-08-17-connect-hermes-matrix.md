# Connect the Hermes Coder Workspace to Matrix

Date: 2026-08-17

## Problem

The local `@hermes-bot:matrix.tom-mendy.com` account and access token existed,
but the Coder workspace template did not receive Matrix credentials. The bot
also needed an explicit human allowlist so federation could not turn Hermes
into a publicly usable agent.

## Reasoning and commands

The existing dedicated `matrix-k8s-auth` identity already reads `/matrix`.
Rather than introduce another identity or copy a token into Hermes' persistent
home, a second `InfisicalStaticSecret` target creates `hermes-matrix` in
`coder-workspaces`. It contains only the access token and allowed Matrix IDs.

The live namespace was checked before editing:

```bash
kubectl get deployment,pod,pvc -n coder-workspaces -o wide
```

It returned `No resources found`, confirming that no existing Hermes workspace
needed migration. A first attempt to inspect a Hermes pod consequently failed
with an empty JSONPath array; this established that the workspace still had to
be created in Coder.

Official Hermes configuration uses `MATRIX_HOMESERVER`, `MATRIX_ACCESS_TOKEN`,
and `MATRIX_ALLOWED_USERS`. The template also supplies a stable bot user and
device ID. Encryption starts in `optional` mode so the first gateway can report
whether the pinned image has all native E2EE dependencies; it can be made
required after that check.

A local Docker inspection was attempted against the pinned Hermes digest. The
daemon repeatedly reported layers as pulling but did not retain an inspectable
image, so E2EE support was not assumed from an incomplete test.

Validation commands:

```bash
helm lint kubernetes/matrix
helm template matrix kubernetes/matrix >/tmp/matrix-rendered.yaml
terraform fmt -check kubernetes/coder/workspace-templates/hermes-personal/main.tf
./scripts/check-storage-policy.sh
rumdl check kubernetes/coder/README.md kubernetes/matrix/README.md \
  docs/activity_report/2026-08-17-connect-hermes-matrix
```

Helm lint, Terraform formatting, the storage policy, Markdown checks, and diff
checks passed. Kubeconform parsed 22 rendered resources: 18 standard resources
were valid and four Infisical custom resources were skipped because their CRD
schemas are not in the standard registry; there were no invalid resources or
errors.

## Outcome

The Matrix chart now distributes the Hermes-only Secret to `coder-workspaces`,
and the Coder template injects the Matrix endpoint, bot identity, token,
allowlist, stable device ID, and optional E2EE mode. The remaining operator
steps are to set `HERMES_MATRIX_ALLOWED_USERS`, reconcile Matrix, publish the
updated Coder template, create the workspace, and complete Hermes model and
memory setup once.
