# Flux Operator GitOps

## Purpose

Flux Operator installs and updates Flux. Native Flux sources and HelmReleases
reconcile the applications in this repository. ResourceSets are not used. The
Flux web UI is available through Authentik at
`https://flux.home.tom-mendy.com`.

The Flux source is the private Forgejo repository at
`ssh://git@forgejo.forgejo.svc.cluster.local/Tom-Mendy/homelab.git`.

## Prerequisites

- A working Kubernetes cluster and kubeconfig.
- Helm 3.8 or newer.
- A new read-only Forgejo deploy key. Do not reuse the former Argo CD key.
- A trusted `known_hosts` file collected for the Forgejo SSH service.
- A current backup of application data and Kubernetes resources.
- The Authentik OIDC Infisical identity and secrets described below.

Never commit the private deploy key, kubeconfig, or Secret YAML.

## Install Flux beside Argo CD

Create a Kubernetes-auth Machine Identity named `authentik-oidc-sync` in
Infisical. Allow the `authentik/authentik-infisical-sync` ServiceAccount to use
it and grant read-only recursive access to `/oidc` in `homelab/prod`.

Create independent client secrets in Infisical. Use a separate value for each
client:

| Path    | Key                                   |
| ------- | ------------------------------------- |
| `/oidc` | `FORGEJO_OIDC_CLIENT_SECRET`          |
| `/oidc` | `GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET` |
| `/oidc` | `FLUX_WEB_CLIENT_SECRET`              |
| `/oidc` | `INFISICAL_OIDC_CLIENT_SECRET`        |

Set `oidc.infisical.identityID` in `kubernetes/authentik/values.yaml` to the
Machine Identity ID. The ID selects an Infisical identity but does not
authenticate by itself. The chart creates the Kubernetes Secret reference, so
namespace recovery does not require a manual bootstrap step. Never put an
Infisical access token or client secret in Git.

Install the consolidated Authentik chart and wait for Infisical to distribute
the scoped Secrets:

```bash
helm upgrade --install authentik kubernetes/authentik \
  --namespace authentik \
  --create-namespace
kubectl -n authentik wait \
  infisicalauth/authentik-oidc-infisical \
  --for=condition=secrets.infisical.com/IsReady \
  --timeout=5m
kubectl -n authentik wait \
  infisicalstaticsecret/authentik-oidc \
  --for=condition=secrets.infisical.com/LastReconcileStatus \
  --timeout=5m
kubectl get secret -n authentik authentik-oidc
kubectl get secret -n forgejo forgejo-oidc
kubectl get secret -n grafana grafana-oidc
kubectl get secret -n flux-system flux-web-client
```

The Infisical OIDC client is declared in the Authentik blueprint. Its secret is
distributed to Authentik as `INFISICAL_OIDC_CLIENT_SECRET`; Infisical itself
stores the client configuration in its organization SSO settings.

Wait for Authentik to apply the Blueprint, then add the cluster administrator to
`homelab-admins` in Authentik:

```bash
kubectl -n authentik rollout status deployment/authentik-worker
```

When migrating an existing cluster, use two Git revisions. The first revision
adds `helm.sh/resource-policy: keep` to every resource rendered by the old
`authentik-extras` and `authentik-postgres` charts. Reconcile both releases and
verify the annotation is present in their stored Helm manifests. This prevents
their uninstall from deleting the Namespace, database Cluster, or bootstrap
resources.

Before applying the consolidation revision, suspend the old releases and
transfer ownership of their Namespace, Cluster, ConfigMap, Ingresses, and
Infisical resources to the `authentik` release:

```bash
flux suspend helmrelease authentik -n flux-system
flux suspend helmrelease authentik-extras -n flux-system
flux suspend helmrelease authentik-postgres -n flux-system

for resource in \
  namespace/authentik \
  cluster.postgresql.cnpg.io/authentik-postgres \
  configmap/authentik-oidc-blueprint \
  ingress/hindsight-authentik-outpost \
  ingress/radarr-authentik-outpost \
  ingress/sonarr-authentik-outpost \
  infisicalauth/authentik-oidc-infisical \
  infisicalconnection/authentik-oidc-infisical \
  infisicalstaticsecret/authentik-oidc \
  secret/authentik-oidc-infisical-identity \
  serviceaccount/authentik-infisical-sync; do
  kubectl annotate "$resource" -n authentik \
    meta.helm.sh/release-name=authentik \
    meta.helm.sh/release-namespace=authentik \
    --overwrite
  kubectl label "$resource" -n authentik \
    app.kubernetes.io/managed-by=Helm --overwrite
done
```

Apply the consolidation revision, then verify the PostgreSQL PVC, Authentik
Deployments, generated Secrets, and OIDC resources before removing the old
HelmRelease objects from Git.

If the old release starts deleting the `authentik` namespace, suspend the new
release immediately. Do not let CloudNativePG create a fresh database. The
`Retain` policy preserves the NFS PV, but the replacement
`authentik-postgres-1` PVC must be bound to the PV that contains
`pgdata/PG_VERSION` before reconciliation resumes. Check the NFS contents
rather than choosing a PV by age or name. The chart recreates the Infisical
identity reference after the namespace returns.

Install Flux Operator with its TLS ingress and Authentik OIDC login. The client
secret travels through stdin and is not written to Git or the shell history:

```bash
kubectl -n flux-system get secret flux-web-client \
  -o jsonpath='{.data.FLUX_WEB_CLIENT_SECRET}' | base64 -d | \
  helm upgrade --install flux-operator \
    oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
    --version '0.58.x' \
    --namespace flux-system \
    --create-namespace \
    --values kubernetes/flux/bootstrap/values.yaml \
    --set-file web.config.authentication.oauth2.clientSecret=/dev/stdin \
    --wait
```

Apply the group-to-Kubernetes role bindings:

```bash
kubectl apply -f kubernetes/flux/bootstrap/web-rbac.yaml
```

Create the Flux SSH Secret from local files:

```bash
kubectl -n flux-system create secret generic flux-system \
  --from-file=identity=/path/to/flux-forgejo \
  --from-file=identity.pub=/path/to/flux-forgejo.pub \
  --from-file=known_hosts=/path/to/known_hosts \
  --dry-run=client -o yaml | kubectl apply -f -
```

Apply the Flux instance:

```bash
kubectl apply -f kubernetes/flux/bootstrap/flux-instance.yaml
kubectl -n flux-system wait fluxinstance/flux \
  --for=condition=Ready --timeout=10m
```

Verify that Flux can fetch Forgejo before stopping Argo CD:

```bash
kubectl -n flux-system get fluxinstance,gitrepository,kustomization
kubectl -n flux-system describe gitrepository flux-system
curl -I https://flux.home.tom-mendy.com
```

## Cut over from Argo CD

This is a maintenance-window operation. The repository change removing
`kubernetes/argocd` must not reach Forgejo before Flux is installed.

1. Confirm every Argo application is healthy and capture meaningful live drift
   in Git. Do not commit bound PVC `volumeName` changes or generated Secrets.
2. Back up critical data and record PVC/PV bindings and workload status.
3. Stop Argo reconciliation without deleting its Applications:

   ```bash
   kubectl -n argocd scale deployment argocd-application-controller --replicas=0
   ```

4. Push this Flux migration to Forgejo.
5. Wait for Flux to adopt the existing Helm releases and resources:

   ```bash
   kubectl -n flux-system wait gitrepository/flux-system \
     --for=condition=Ready --timeout=5m
   kubectl -n flux-system get helmrepositories,ocirepositories
   kubectl -n flux-system get helmreleases
   kubectl -n flux-system wait helmrelease --all \
     --for=condition=Ready --timeout=30m
   ```

6. Validate pods, ingress, databases, Infisical Secrets, runners, and PVCs.
7. Remove Argo CD without cascading application resources:

   ```bash
   kubectl -n argocd get applications -o name \
     | xargs -r -n1 kubectl -n argocd patch --type=merge \
       -p '{"metadata":{"finalizers":null}}'
   kubectl -n argocd delete applications --all --wait=true
   helm uninstall argocd --namespace argocd
   kubectl delete namespace argocd
   ```

## Rollback

If Flux adoption fails, stop Flux reconciliation and restore Argo before
removing any Argo object:

```bash
kubectl -n flux-system patch kustomization flux-system --type=merge \
  -p '{"spec":{"suspend":true}}'
kubectl -n argocd scale deployment argocd-application-controller --replicas=1
```

After correcting Git, resume Flux with:

```bash
kubectl -n flux-system patch kustomization flux-system --type=merge \
  -p '{"spec":{"suspend":false}}'
```

## Validation

```bash
kubectl kustomize --load-restrictor=LoadRestrictionsNone \
  kubernetes/flux/cluster
./scripts/test-helm-chart.sh
./scripts/kubeconform-local-charts.sh
./scripts/check-storage-policy.sh
rg -n 'local-path' kubernetes
rumdl check --fix .
```

Flux controller caches are ephemeral and do not contain application data. All
persistent workload storage remains on `nfs-k8s` or approved static Synology NFS
volumes.

## Recovery limitation

Forgejo runs inside this cluster, so a total cluster rebuild cannot bootstrap
Flux until Forgejo and its NFS-backed data are restored and reachable. Keep an
external repository backup and the deploy key recovery material outside the
cluster.
