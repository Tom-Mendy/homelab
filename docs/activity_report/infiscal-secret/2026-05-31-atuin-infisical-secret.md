# Move Atuin Database Secret to Infisical

## Problem

Atuin committed its PostgreSQL password in `kubernetes/atuin/values.yaml`.
The Atuin and PostgreSQL deployments consume the Kubernetes Secret
`atuin-secrets`, so the migration must preserve that Secret name and keys:

```text
ATUIN_DB_USERNAME
ATUIN_DB_PASSWORD
ATUIN_DB_URI
```

## Reasoning path

This first step moves the existing database credentials to Infisical without
rotating the live PostgreSQL password. Password rotation should be a separate
database migration after the Secret source is stable.

The Kubernetes Auth machine identity is:

```text
name: atuin-k8s-auth
identityID: 7b4de8a4-b92f-4694-8183-4b026262442f
namespace: atuin
service account: atuin-infisical-sync
```

Infisical project `homelab`, env `prod`, path `/atuin` must contain:

```text
ATUIN_DB_USERNAME
ATUIN_DB_PASSWORD
ATUIN_DB_URI
```

## Commands and results

Render the chart:

```sh
helm template test kubernetes/atuin
```

Expected resources include:

```text
ServiceAccount atuin-infisical-sync
Secret atuin-infisical-identity
InfisicalConnection atuin-infisical
InfisicalAuth atuin-infisical
InfisicalStaticSecret atuin-secrets
```

Validate against live CRDs without applying:

```sh
helm template test kubernetes/atuin > /tmp/atuin-infisical-render.yaml
kubectl apply --dry-run=server -f /tmp/atuin-infisical-render.yaml
```

Run repository checks:

```sh
kubernetes/test-helm-chart.sh
./scripts/check-storage-policy.sh
```

Expected storage result:

```text
storage policy ok
```

## Final outcome

The committed Atuin database password was removed from Git. Infisical now owns
the `atuin-secrets` Kubernetes Secret consumed by Atuin and PostgreSQL.
