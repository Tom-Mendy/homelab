# Move Traefik Cloudflare Token to Infisical

## Problem

The Traefik Cloudflare DNS token was stored in Git in the Traefik local Helm
chart and in the manual example manifest. This token controls DNS records used
for ACME DNS-01 certificate issuance, so it must be treated as compromised and
rotated outside Git.

## Reasoning path

Traefik already reads the token from a Kubernetes Secret named
`traefik-cloudflare-dns` with key `CF_DNS_API_TOKEN`:

```yaml
env:
  - name: CF_DNS_API_TOKEN
    valueFrom:
      secretKeyRef:
        name: traefik-cloudflare-dns
        key: CF_DNS_API_TOKEN
```

The safest local chart change is to keep that Secret name and key stable, but
change the producer from a committed Kubernetes Secret to the Infisical
operator. The Infisical operator pattern already exists in the repository for
authentik, so Traefik now follows the same shape:

```yaml
infisicalSecret:
  enabled: false
  name: traefik-cloudflare-dns
  serviceAccountName: traefik-infisical-sync
  hostAPI: https://infisical.home.tom-mendy.com/api
  identityID: ""
  projectId: "758123bc-7eaa-4256-98a2-bb7438a783b8"
  envSlug: prod
  secretsPath: /traefik
```

Before live sync, store the rotated token in Infisical project `homelab`, env
`prod`, path `/traefik`:

```text
CF_DNS_API_TOKEN=<rotated-cloudflare-dns-token>
```

Then set `infisicalSecret.enabled=true` and fill the real Infisical
`identityID` in `kubernetes/traefik/values.yaml`.

## Commands and results

Render the default Traefik local chart. The default no longer renders a Secret
with a committed token.

```sh
helm template test kubernetes/traefik
```

Result:

```text
```

Render the Infisical-enabled path with a dummy identity ID to verify the
ServiceAccount and InfisicalSecret shape.

```sh
helm template test kubernetes/traefik \
  --set infisicalSecret.enabled=true \
  --set infisicalSecret.identityID=dummy-identity
```

Result:

```text
# Source: traefik-local-extras/templates/serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: traefik-infisical-sync
  namespace: traefik
---
# Source: traefik-local-extras/templates/infisical-secret.yaml
apiVersion: secrets.infisical.com/v1alpha1
kind: InfisicalSecret
metadata:
  name: traefik-cloudflare-dns
  namespace: traefik
spec:
  hostAPI: "https://infisical.home.tom-mendy.com/api"
  syncConfig:
    resyncInterval: 1m
    instantUpdates: false
  authentication:
    kubernetesAuth:
      identityId: "dummy-identity"
      autoCreateServiceAccountToken: true
      serviceAccountRef:
        name: traefik-infisical-sync
        namespace: traefik
      secretsScope:
        projectId: "758123bc-7eaa-4256-98a2-bb7438a783b8"
        envSlug: "prod"
        secretsPath: "/traefik"
        recursive: false
  managedKubeSecretReferences:
    - secretName: traefik-cloudflare-dns
      secretNamespace: traefik
      creationPolicy: Orphan
      template:
        includeAllSecrets: true
```

Render all local charts covered by the existing script.

```sh
kubernetes/test-helm-chart.sh
```

Result:

```text
=== blocky ===
OK
=== homepage ===
OK
=== traefik ===
OK
=== keel ===
OK
=== prometheus ===
OK
=== grafana ===
OK
=== navidrome ===
OK
=== vaultwarden ===
OK
=== forgejo ===
OK
=== forgejo-runner ===
OK
=== searxng ===
OK
=== endfield ===
OK
=== infisical-postgres ===
OK
=== authentik-postgres ===
OK
=== authentik ===
OK
```

Check repository storage policy.

```sh
./scripts/check-storage-policy.sh
```

Result:

```text
storage policy ok
```

Check the touched Traefik files and docs no longer contain non-empty
`apiToken` values.

```sh
rg -n '[a]piToken: "[^"]+"' \
  kubernetes/traefik docs/acme-dns01-private-services.md
```

Result:

```text
```

## Final outcome

The committed Cloudflare token was removed from the Traefik chart and example
manifest. The chart can now render an InfisicalSecret that creates the same
Kubernetes Secret Traefik already consumes. Live cutover still requires a
rotated Cloudflare token in Infisical and the real Infisical Kubernetes-auth
machine identity ID in `kubernetes/traefik/values.yaml`.

## Live verification update

The first live check showed Kubernetes Auth loaded the machine identity token,
but secret sync failed because the project slug lookup returned 404:

```text
Project with slug 'homelab' not found
```

The URL segment after `/projects/` is the Infisical product area, not the
project slug. To avoid slug ambiguity, the Traefik values now use project ID
from the Infisical project URL:

```yaml
projectId: "758123bc-7eaa-4256-98a2-bb7438a783b8"
```
