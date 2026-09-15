# Move SearXNG Secrets to Infisical

## Problem

SearXNG committed two sensitive values in `kubernetes/searxng/values.yaml`:

- `server-secret-key`
- `WIREGUARD_PRIVATE_KEY`

The deployment consumes two Kubernetes Secrets, so the migration must preserve
those Secret names and keys:

```text
searxng-secret/server-secret-key
searxng-vpn-secret/WIREGUARD_PRIVATE_KEY
```

## Reasoning path

The SearXNG local chart already templates both Kubernetes Secrets. The safe
migration is to disable literal Secret rendering and have one
`InfisicalStaticSecret` write both target Secrets from Infisical path
`/searxng`.

The Kubernetes Auth machine identity is:

```text
name: searxng-k8s-auth
identityID: c4027cca-f8d6-4d36-a73c-2dc61baf2016
namespace: searxng
service account: searxng-infisical-sync
```

Infisical project `homelab`, env `prod`, path `/searxng` must contain:

```text
server-secret-key=<rotated-searxng-secret>
WIREGUARD_PRIVATE_KEY=<rotated-wireguard-private-key>
```

## Commands and results

Render the chart:

```sh
helm template test kubernetes/searxng
```

Expected resources include:

```text
ServiceAccount searxng-infisical-sync
Secret searxng-infisical-identity
InfisicalConnection searxng-infisical
InfisicalAuth searxng-infisical
InfisicalStaticSecret searxng-secrets
```

Validate the rendered chart against live cluster CRDs without applying it:

```sh
helm template test kubernetes/searxng > /tmp/searxng-infisical-render.yaml
kubectl apply --dry-run=server -f /tmp/searxng-infisical-render.yaml
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

The committed SearXNG app secret and WireGuard private key were removed from
Git. The chart now uses Infisical to create the same Kubernetes Secrets consumed
by the existing deployment.
