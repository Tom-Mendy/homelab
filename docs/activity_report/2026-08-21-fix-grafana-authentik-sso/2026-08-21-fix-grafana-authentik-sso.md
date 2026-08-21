# Fix Grafana Authentik SSO

## Problem

Grafana redirected to Authentik successfully, but the OAuth callback failed
while exchanging the authorization code for tokens:

```text
oauth2: "invalid_client" "Client authentication failed (e.g., unknown client,
no client authentication included, or unsupported authentication method)"
```

## Reasoning and investigation

The repository configuration was inspected with:

```sh
rg -n -i -C 4 'grafana|oauth|oidc|authentik' \
  kubernetes/grafana kubernetes/authentik kubernetes/flux docs
```

The Grafana callback URL and Authentik redirect URI both use
`https://grafana.home.tom-mendy.com/login/generic_oauth`. Grafana uses client ID
`grafana`, while Authentik defines the same client ID. The token exchange error
therefore points to the shared client secret or its formatting, rather than to
the callback URL, group binding, or Grafana role mapping.

The secret is distributed from Infisical into separate Kubernetes Secrets for
Authentik and Grafana. Both target templates previously copied the Infisical
value without trimming whitespace. A pasted trailing newline or surrounding
whitespace could make the two OAuth clients reject the exchange.

## Change

The Infisical target template now applies `trim` to
`GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET` in both destinations:

- the `authentik-oidc` Secret used by Authentik's global environment;
- the `grafana-oidc` Secret used by Grafana's environment.

This keeps the secret out of Git while ensuring both workloads receive the same
normalized value after Infisical reconciliation.

## Validation

The following commands were run without displaying secret values:

```sh
helm template authentik-extras kubernetes/authentik >/tmp/authentik-extras-rendered.yaml
helm template grafana kubernetes/grafana >/tmp/grafana-rendered.yaml
git diff --check
helm lint kubernetes/authentik
helm lint kubernetes/grafana
./scripts/check-storage-policy.sh
```

The first live cluster check found different secret values:

```text
grafana byte count: 128
authentik byte count: 32
```

The Grafana namespace contained an obsolete `InfisicalStaticSecret` named
`grafana-oidc`. It read from the old Infisical `/grafana` path and competed
with the canonical `/oidc` target declared by the Authentik extras chart.
Its manifest was inspected without printing secret data:

```text
namespace: grafana
name: grafana-oidc
secretPath: /grafana
target: grafana/grafana-oidc
```

That stale sync object was deleted. The canonical target then recreated the
Grafana Secret with the same value as Authentik:

```text
grafana secret hash: <same as authentik>
authentik secret hash: <same as grafana>
grafana byte count: 32
grafana InfisicalStaticSecret objects: none
canonical sync: Reconciliation successful
```

Grafana was restarted and successfully loaded the canonical secret hash. Its
recent logs contained no new OAuth token-exchange or `invalid_client` errors.

## Outcome

The repository now prevents whitespace corruption when the Grafana OAuth
client secret is distributed. The live stale-sync conflict was removed, both
workloads now use the same 32-byte client secret, and Grafana has been
restarted. The remaining acceptance step is a browser login through Authentik.
