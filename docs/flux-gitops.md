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
- An Authentik OAuth2/OpenID provider with client ID `flux-web`.

Never commit the private deploy key, kubeconfig, or Secret YAML.

## Install Flux beside Argo CD

In Authentik, create an OAuth2/OpenID provider and application with:

- slug: `flux-web`
- client ID: `flux-web`
- redirect URI: `https://flux.home.tom-mendy.com/oauth2/callback`
- scopes: `openid`, `profile`, `email`, `offline_access`, and `groups`

Create the `flux-admins` and `flux-viewers` Authentik groups, then add users to
the appropriate group. Export the generated client secret only for the current
shell:

```bash
read -rsp 'Authentik Flux client secret: ' FLUX_WEB_CLIENT_SECRET
export FLUX_WEB_CLIENT_SECRET
```

Install Flux Operator with its TLS ingress and Authentik OIDC login:

```bash
printf '%s' "$FLUX_WEB_CLIENT_SECRET" | \
  helm upgrade --install flux-operator \
    oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
    --version '0.58.x' \
    --namespace flux-system \
    --create-namespace \
    --values kubernetes/flux/bootstrap/values.yaml \
    --set-file web.config.authentication.oauth2.clientSecret=/dev/stdin \
    --wait
unset FLUX_WEB_CLIENT_SECRET
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
