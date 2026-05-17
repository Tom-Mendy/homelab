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
string. CloudNativePG generates the application database secret as
`infisical-postgres-app`, including a `uri` key that Infisical can consume.

## Commands to run

Create the Infisical bootstrap secret before syncing the `infisical` Argo CD
app. CloudNativePG generates `infisical-postgres-app` for database credentials;
do not put the database password in Git or in the Infisical bootstrap secret.

```sh
kubectl create namespace infisical

kubectl create secret generic infisical-secrets \
  --namespace infisical \
  --from-literal=AUTH_SECRET="$(openssl rand -base64 32)" \
  --from-literal=ENCRYPTION_KEY="$(openssl rand -hex 16)" \
  --from-literal=SITE_URL="https://infisical.home.tom-mendy.com" \
  --dry-run=client -o yaml | kubectl apply -f -
```

CloudNativePG generates `authentik-postgres-app` for the authentik database.
The authentik chart reads `AUTHENTIK_POSTGRESQL__PASSWORD` directly from that
secret and sets the other PostgreSQL connection fields as explicit environment
variables.

After Infisical is reachable, finish its first-user setup in the browser:

```text
https://infisical.home.tom-mendy.com
```

Then create an Infisical project for the homelab, add a Kubernetes-auth machine
identity for the cluster, and store these authentik keys under `/authentik`:

```text
AUTHENTIK_ENABLED=true
AUTHENTIK_SECRET_KEY=<openssl rand -base64 60>
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
kubectl get crd clusters.postgresql.cnpg.io poolers.postgresql.cnpg.io
kubectl get deploy,pods -n cnpg-system
kubectl get clusters.postgresql.cnpg.io -A
kubectl get secret -n infisical infisical-postgres-app
kubectl get pods -n infisical
kubectl get ingress -n infisical
kubectl get secret -n authentik authentik-postgres-app
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

The first Argo CD deployment attempt exposed two ordering/apply issues:

```text
CustomResourceDefinition.apiextensions.k8s.io "clusters.postgresql.cnpg.io"
is invalid: metadata.annotations: Too long: may not be more than 262144 bytes

Cluster.postgresql.cnpg.io "" not found
```

The fix is to use server-side apply for the CloudNativePG chart and skip dry-run
for CNPG `Cluster` resources while the CRD is being installed:

```yaml
syncOptions:
  - ServerSideApply=true
```

```yaml
syncOptions:
  - SkipDryRunOnMissingResource=true
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
