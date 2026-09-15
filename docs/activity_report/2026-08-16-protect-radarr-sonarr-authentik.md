# Protect Radarr and Sonarr with authentik SSO

## Problem

Radarr and Sonarr need a browser SSO login through authentik, with a separate
authentik application and access rule for each service. Neither application
supports native OIDC or PostgreSQL.

## Reasoning and commands

The existing `/config` PVCs for both applications use `nfs-k8s`, which keeps
their SQLite state available when the workload moves between worker nodes.
CloudNativePG cannot replace this SQLite database because Radarr and Sonarr
do not support PostgreSQL.

Authentik Proxy Providers support applications without native OIDC. The
`forward_single` mode keeps Traefik as the reverse proxy, checks each request
through the embedded outpost, and needs the
`/outpost.goauthentik.io` path to reach that outpost without the authentication
middleware.

```sh
kubectl -n media get pvc,pods,ingress
kubectl -n authentik get pods,svc
kubectl get crd middlewares.traefik.io -o jsonpath='{.spec.versions[*].name}'
```

The inspection showed bound `nfs-k8s` PVCs for Radarr and Sonarr, a running
embedded authentik outpost on `authentik-server`, and the Traefik Middleware
CRD as `v1alpha1`.

The configuration files also reported `AuthenticationMethod` as `Forms` and
`AuthenticationRequired` as `Enabled`. Each deployment therefore uses a small
init container based on its already-pinned application image to set those
values to `None` and `Disabled` before the application starts.

```sh
helm lint kubernetes/media
helm template media kubernetes/media --namespace media
helm lint kubernetes/authentik
kubectl kustomize kubernetes/flux/cluster/apps \
  --load-restrictor LoadRestrictionsNone
./scripts/check-storage-policy.sh
```

Both Helm charts linted and rendered successfully. The complete Flux
kustomization rendered successfully, and the storage policy command reported
`storage policy ok`.

## Outcome

The authentik blueprint creates separate Radarr and Sonarr applications and
providers. Both grant access to `homelab-admins` and `media-users`. The media
chart creates one Traefik middleware, routes each outpost callback path to the
embedded outpost, and applies the middleware only to the application routes.
The local Radarr and Sonarr login forms are disabled so authentik remains the
only browser login.
