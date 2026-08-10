# Manage Authentik OIDC clients as code

## Problem

Forgejo and Grafana providers had been created manually in Authentik, while the
new Flux Operator Web UI still needed a provider. Client secrets and client-side
configuration were not consistently reconciled from Git.

## Reasoning

Authentik 2026.5.2 supports native Blueprints mounted by its Helm chart. A
Blueprint can adopt the existing Forgejo and Grafana objects through their
stable names and create Flux without adding Terraform or another controller.

The client secrets remain in Infisical. One Kubernetes-auth Machine Identity
reads only `/oidc` and an `InfisicalStaticSecret` distributes a target Secret to
each client namespace. Each target exposes only its own client secret.

All clients use confidential authorization-code flow with refresh tokens,
strict redirect URIs, and the standard OpenID scopes. Authentik access is based
on application groups; `homelab-admins` retains administrative access.

Forgejo stores authentication sources in its database rather than `app.ini`.
Its chart therefore runs a small idempotent post-start script that adds or
updates the `authentik` source with the native Forgejo CLI. Grafana and Flux use
their native Helm configuration.

## Commands and results

The first model inventory command used an obsolete Python import and failed
without changing Authentik:

```text
ModuleNotFoundError: No module named 'authentik_core'
```

The corrected read-only inventory found two providers and no Flux groups:

```text
OAUTH2_PROVIDERS
4 Grafana grafana https://grafana.home.tom-mendy.com/login/generic_oauth
1 forgejo <existing-client-id> https://forgejo.tom-mendy.com/user/oauth2/authentik/callback
FLUX_GROUPS
```

The live chart and CRD inspection confirmed Blueprint ConfigMap mounts,
`global.envFrom`, multiple Infisical sources, and per-target templates. Static
validation commands were:

```bash
sh kubernetes/forgejo/files/configure-oidc.sh --self-test
helm template test kubernetes/authentik
helm template test kubernetes/forgejo
helm template test kubernetes/grafana
kubectl kustomize --load-restrictor=LoadRestrictionsNone \
  kubernetes/flux/cluster
./scripts/test-helm-chart.sh
./scripts/check-storage-policy.sh
rumdl check --fix README.md docs/flux-gitops.md \
  docs/authentik-infisical-guest-checklist.md \
  docs/activity_report/2026-08-10-authentik-oidc-as-code/*.md
```

The pinned Grafana chart could not be downloaded from the repository index
currently served upstream:

```text
Error: chart "grafana" version "12.4.1" not found
```

The live release values confirmed that `envValueFrom` and `grafana.ini` are
supported. Local rendering and dependency checks completed successfully:

```text
23 local charts: OK
storage policy ok
helmreleases=38 ordered=38
```

Kubeconform reported no invalid local-chart resources. The cluster API also
accepted the rendered custom resources without applying them:

<!-- rumdl-disable MD013 -->

```text
$ kubectl apply --dry-run=server -f /tmp/authentik-oidc-local.yaml
configmap/authentik-oidc-blueprint created (server dry run)
infisicalauth.secrets.infisical.com/authentik-oidc-infisical created (server dry run)
infisicalconnection.secrets.infisical.com/authentik-oidc-infisical created (server dry run)
infisicalstaticsecret.secrets.infisical.com/authentik-oidc created (server dry run)

$ kubectl apply --dry-run=server -f /tmp/forgejo-oidc.yaml
deployment.apps/forgejo configured (server dry run)
configmap/forgejo-oidc-script created (server dry run)
```

<!-- rumdl-enable MD013 -->

## Final outcome

The repository now declares the Forgejo, Grafana, and Flux OIDC providers,
applications, groups, access bindings, client configuration, and secret
distribution. The live rotation remains gated on creating the Infisical
Machine Identity and the three new secret values; no secret is stored in Git.
## Cluster verification

The first reconciliation showed that `authentik-infisical-sync` was missing. The
local chart template was still gated by the retired `infisicalSecret.enabled`
flag, so it was changed to create the ServiceAccount when OIDC Infisical sync
is configured. The ServiceAccount was created and the Infisical operator was
restarted.

Commands and observed results:

```text
kubectl -n authentik get infisicalauth authentik-oidc-infisical -o json
message: ServiceAccount "authentik-infisical-sync" not found

kubectl -n authentik create serviceaccount authentik-infisical-sync --dry-run=client -o yaml | kubectl apply -f -
serviceaccount/authentik-infisical-sync created

kubectl -n infisical-operator rollout restart deployment/infisical-opera-controller-manager
deployment "infisical-opera-controller-manager" successfully rolled out

kubectl -n authentik get infisicalauth authentik-oidc-infisical -o json
message: InfisicalAuth is ready to be used.

kubectl -n authentik get infisicalstaticsecret authentik-oidc -o json
message: Reconciliation failed: unable to fetch all secret sources: Unauthorized access: status 403
```

The Kubernetes authentication is now healthy. Secret synchronization remains
blocked by Infisical project/path permissions for the configured identity; no
secret values were displayed.
