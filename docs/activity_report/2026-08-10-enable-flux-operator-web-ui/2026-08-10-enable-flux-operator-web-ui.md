# Enable the Flux Operator web UI

## Problem

The Flux Operator bootstrap disabled its web server. The cluster owner wanted
the status interface exposed internally without allowing unauthenticated access
to cluster information or GitOps actions.

## Reasoning

Flux Operator already supports a native Web UI, Kubernetes Ingress, and OIDC.
Using those chart features avoids an extra proxy deployment. Authentik is the
existing identity provider, Traefik is the existing ingress controller, and the
private DNS zone already maps application hostnames to `10.0.0.60`.

The OAuth2 client secret is not stored in Git. The bootstrap command reads it
from the operator's shell and passes it directly to Helm. Authentik groups map
to the predefined Flux web roles:

- `flux-admins` maps to `flux-web-admin`.
- `flux-viewers` maps to `flux-web-user`.

## Commands and results

The first chart inspection failed because DNS access to GHCR was unavailable in
the sandbox:

```text
$ helm show values oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
    --version 0.58.0
Error: ... lookup ghcr.io: Temporary failure in name resolution
```

The command succeeded with approved network access and confirmed the native
web, Ingress, RBAC, and configuration values:

```text
Pulled: ghcr.io/controlplaneio-fluxcd/charts/flux-operator:0.58.0
Digest: sha256:1ccf038123198fab1923b3fc4977154bd4cc3729f4c7d957dedf09478d9d19d5
```

A client-side apply attempt could not download the cluster OpenAPI schema from
inside the sandbox, so the manifests were validated statically instead:

```text
$ kubectl apply --dry-run=client \
    -f kubernetes/flux/bootstrap/web-rbac.yaml
error validating data: failed to download openapi: ... operation not permitted
```

Render and policy validation commands:

```bash
helm template flux-operator \
  oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
  --version 0.58.0 \
  --namespace flux-system \
  --values kubernetes/flux/bootstrap/values.yaml \
  --set-string web.config.authentication.oauth2.clientSecret=test-only
./scripts/check-storage-policy.sh
rumdl check --fix docs/flux-gitops.md \
  docs/activity_report/2026-08-10-enable-flux-operator-web-ui/*.md \
  docs/activity_report/2026-08-10-migrate-argocd-to-flux/*.md
```

The rendered chart contained the expected endpoint and predefined roles:

```text
flux-operator  traefik  flux.home.tom-mendy.com
flux-web-user
flux-web-admin
```

The final repository checks succeeded:

```text
storage policy ok
Success: No issues found in 3 files
```

## Final outcome

The Flux Operator chart now enables its web UI at
`https://flux.home.tom-mendy.com`, terminates TLS through Traefik, and redirects
login to Authentik. Blocky and Homepage include the new endpoint. The Authentik
provider, groups, and client secret must be created before installing the
operator, as documented in `docs/flux-gitops.md`. No live cluster resource was
changed during this activity.
