# Fix the Authentik Embedded Outpost for Radarr and Sonarr

## Problem

Opening Radarr or Sonarr through Authentik displayed the Authentik `Not Found`
page. The dedicated callback ingresses already routed
`/outpost.goauthentik.io` to the Authentik server, but the documented outpost
health endpoint returned HTTP `404` instead of `204`.

## Investigation and reasoning

The ingress and provider assignments were checked first. Both applications
used single-application forward-auth providers assigned to the embedded
outpost, so changing Traefik again would only have hidden the actual failure.

The Authentik server logs identified the root cause:

```text
Failed to fetch outpost configuration, retrying in 3 seconds
invalid header field value for "Authorization"
```

The active server environment was inspected without printing the secret:

```sh
kubectl -n authentik exec deploy/authentik-server -- sh -c \
  'printf %s "$AUTHENTIK_SECRET_KEY" | wc -c'
```

Result before the fix:

```text
81
```

The value ended with a line feed. That byte made the embedded outpost's local
authorization header invalid. The existing `authentik-secrets` Secret was also
orphaned: only the `/oidc` Infisical source was still reconciled declaratively.

The deployed Infisical operator was identified as `v0.11.0`. Its official
source confirms that its template engine includes Sprig, so the `trim`
function can safely remove surrounding whitespace while rendering the
Kubernetes Secret.

## Changes

- Added `/authentik` to the existing `InfisicalStaticSecret` sources.
- Added an explicit `authentik-secrets` target containing only the five
  Authentik configuration keys used by the deployment.
- Rendered `AUTHENTIK_SECRET_KEY` through `trim`.
- Removed the disabled legacy `v1alpha1` Infisical template and values.
- Added `secrets.infisical.com/auto-reload: "true"` to both Authentik
  Deployments through the upstream Helm values.
- Reconciled Infisical and restarted the Authentik server and worker once.

The value stored in Infisical differed from the former manually created
Kubernetes Secret. Infisical was retained as the selected source of truth.
Changing `AUTHENTIK_SECRET_KEY` invalidates existing Authentik login sessions,
so users must sign in again; application data is unaffected.

## Commands and results

The local chart rendered successfully and passed Kubernetes API validation:

```sh
helm template authentik-extras kubernetes/authentik \
  --namespace authentik > /tmp/authentik-rendered.yaml
kubectl apply --dry-run=server -f /tmp/authentik-rendered.yaml
```

Result:

```text
infisicalstaticsecret/authentik-oidc configured
```

An attempted direct chart download used an incorrect repository artifact URL
and returned `404`. The already cached official `2026.5.2` package was then
used to confirm that the deployment annotation renders on both workloads:

```text
curl: (22) The requested URL returned error: 404
secrets.infisical.com/auto-reload: "true"
secrets.infisical.com/auto-reload: "true"
```

The Infisical resource reconciled successfully:

```sh
kubectl -n authentik get infisicalstaticsecret authentik-oidc \
  -o jsonpath='{range .status.conditions[*]}{.type}{"="}{.status}{"\n"}{end}'
```

Result:

```text
secrets.infisical.com/LastReconcileStatus=True
secrets.infisical.com/LastReconcileAuthMethod=True
secrets.infisical.com/LastSuccessfulReconcileAt=True
```

Both rollouts completed:

```sh
kubectl -n authentik rollout status deployment/authentik-server --timeout=180s
kubectl -n authentik rollout status deployment/authentik-worker --timeout=180s
```

Result:

```text
deployment "authentik-server" successfully rolled out
deployment "authentik-worker" successfully rolled out
```

The outpost endpoints and forward-auth redirects were tested:

```sh
curl -sk -o /dev/null -w '%{http_code}\n' \
  https://radarr.home.tom-mendy.com/outpost.goauthentik.io/ping
curl -sk -o /dev/null -w '%{http_code}\n' \
  https://sonarr.home.tom-mendy.com/outpost.goauthentik.io/ping
curl -sk -o /dev/null -w '%{http_code}\n' \
  https://radarr.home.tom-mendy.com/
curl -sk -o /dev/null -w '%{http_code}\n' \
  https://sonarr.home.tom-mendy.com/
```

Result:

```text
204
204
302
302
```

## Final outcome

The embedded outpost now loads the Radarr and Sonarr proxy providers. Their
health endpoints return `204`, and unauthenticated application requests are
redirected to Authentik instead of displaying its `Not Found` page.

The Authentik runtime Secret is now continuously synchronized from Infisical,
and future Secret updates trigger rolling restarts of the server and worker.
