# Add Infisical, CloudNativePG, and authentik

## Problem

The cluster needs a self-hosted identity provider and a secrets workflow before
adding single sign-on to the rest of the homelab apps. The identity provider is
authentik. Secrets are managed by Infisical, and both Infisical and authentik
use CloudNativePG-managed PostgreSQL instead of worker-local storage.

The storage policy forbids `local-path`, so all persistent storage added here
uses the shared `nfs-k8s` storage class.

## Reasoning path

The authentik Kubernetes guide installs authentik from its Helm chart and
documents PostgreSQL as a dependency:

```sh
helm repo add authentik https://charts.goauthentik.io
helm repo update
helm upgrade --install authentik authentik/authentik -f values.yaml
```

For this cluster, the chart's bundled PostgreSQL is disabled and replaced by a
CloudNativePG `Cluster`. The CloudNativePG bootstrap reference used for the
database cluster shape is:

```text
https://cloudnative-pg.io/docs/1.29/bootstrap
```

The Infisical Helm chart supports using an existing Kubernetes secret for root
configuration and an existing secret key containing a PostgreSQL connection
string. That lets one bootstrap secret serve both CloudNativePG database owner
credentials and Infisical application configuration.

## Commands to run

Create the Infisical bootstrap secret before syncing the `infisical-postgres`
and `infisical` Argo CD apps. Replace the generated values only by running the
command locally; do not commit them to Git.

```sh
kubectl create namespace infisical

INFISICAL_DB_PASSWORD="$(openssl rand -base64 36)"
INFISICAL_DB_URI="postgresql://infisical:${INFISICAL_DB_PASSWORD}@infisical-postgres-rw.infisical.svc.cluster.local:5432/infisicalDB"

kubectl create secret generic infisical-secrets \
  --namespace infisical \
  --from-literal=username=infisical \
  --from-literal=password="${INFISICAL_DB_PASSWORD}" \
  --from-literal=AUTH_SECRET="$(openssl rand -base64 32)" \
  --from-literal=ENCRYPTION_KEY="$(openssl rand -hex 16)" \
  --from-literal=SITE_URL="https://infisical.home.tom-mendy.com" \
  --from-literal=DB_CONNECTION_URI="${INFISICAL_DB_URI}" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Create the authentik database owner secret before syncing
`authentik-postgres`. Store the same password in Infisical at the
`/authentik` path as `AUTHENTIK_POSTGRESQL__PASSWORD`.

```sh
kubectl create namespace authentik

AUTHENTIK_DB_PASSWORD="$(openssl rand -base64 36)"

kubectl create secret generic authentik-postgres-app \
  --namespace authentik \
  --from-literal=username=authentik \
  --from-literal=password="${AUTHENTIK_DB_PASSWORD}" \
  --dry-run=client -o yaml | kubectl apply -f -
```

After Infisical is reachable, finish its first-user setup in the browser:

```text
https://infisical.home.tom-mendy.com
```

Then create an Infisical project for the homelab, add a Kubernetes-auth machine
identity for the cluster, and store these authentik keys under `/authentik`:

```text
AUTHENTIK_ENABLED=true
AUTHENTIK_SECRET_KEY=<openssl rand -base64 60>
AUTHENTIK_POSTGRESQL__HOST=authentik-postgres-rw.authentik.svc.cluster.local
AUTHENTIK_POSTGRESQL__NAME=authentik
AUTHENTIK_POSTGRESQL__USER=authentik
AUTHENTIK_POSTGRESQL__PASSWORD=<same value used in authentik-postgres-app>
AUTHENTIK_POSTGRESQL__PORT=5432
AUTHENTIK_LOG_LEVEL=info
AUTHENTIK_ERROR_REPORTING__ENABLED=false
AUTHENTIK_WEB__PATH=/
```

Enable the authentik Infisical sync after filling the real Infisical
`identityID` in `kubernetes/authentik/values.yaml`:

```yaml
infisicalSecret:
  enabled: true
  identityID: "<machine-identity-id>"
```

Sync order:

```sh
argocd app sync cloudnative-pg
argocd app sync infisical-postgres
argocd app sync infisical
argocd app sync infisical-operator
argocd app sync authentik-postgres
argocd app sync authentik
```

Verify CloudNativePG, Infisical, and authentik:

```sh
kubectl get clusters.postgresql.cnpg.io -A
kubectl get pods -n infisical
kubectl get ingress -n infisical
kubectl get infisicalsecret -n authentik
kubectl get secret authentik-secrets -n authentik
kubectl get pods -n authentik
kubectl get ingress -n authentik
```

Open the authentik initial setup URL with the required trailing slash:

```text
https://authentik.home.tom-mendy.com/if/flow/initial-setup/
```

## Command results

Local chart rendering succeeded:

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

Storage policy validation succeeded:

```text
storage policy ok
```

Markdown validation succeeded after fixing line length:

```text
Success: No issues found in 24 files
```

The implementation adds these GitOps entry points:

```text
kubernetes/argocd/apps/cloudnative-pg.yaml
kubernetes/argocd/apps/infisical-postgres.yaml
kubernetes/argocd/apps/infisical.yaml
kubernetes/argocd/apps/infisical-operator.yaml
kubernetes/argocd/apps/authentik-postgres.yaml
kubernetes/argocd/apps/authentik.yaml
```

The new database clusters request NFS-backed storage:

```yaml
storage:
  storageClass: nfs-k8s
```

Infisical Redis persistence is also pinned to NFS-backed storage:

```yaml
redis:
  master:
    persistence:
      storageClass: nfs-k8s
```

## Final outcome

CloudNativePG, Infisical, the Infisical operator, and authentik are now modeled
as Argo CD applications. Infisical and authentik have private HTTPS hostnames
through Traefik and Blocky, and Homepage includes links for both services.

The remaining hands-on steps are intentionally limited to secret bootstrap and
first-run identity setup. Real secrets are not committed to the repository.
