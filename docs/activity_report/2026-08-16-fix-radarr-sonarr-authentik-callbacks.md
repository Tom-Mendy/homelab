# Fix Radarr and Sonarr authentik callbacks

## Problem

Opening either the Radarr or Sonarr application from authentik returned the
authentik `Not Found` page. Traefik logs showed that the callback Ingresses
could not be created because they targeted the `media/authentik-outpost`
`ExternalName` Service. The Traefik configuration forbids ExternalName
Services.

## Reasoning and commands

The embedded authentik outpost already serves both proxy providers through
`authentik-server`. The forward-auth middleware can reach that Service by its
cluster DNS name, but the browser callback needs an Ingress route. Instead of
allowing ExternalName Services cluster-wide or adding outpost deployments, the
callback routes are defined in the `authentik` namespace and target the local
Service directly.

```sh
kubectl -n media get ingress,middleware,svc
kubectl -n authentik logs deployment/authentik-server
kubectl -n traefik logs deployment/traefik
```

The decisive Traefik result was:

```text
Cannot create service error="externalName services not allowed: media/authentik-outpost"
```

The initial instance-logo probe did not provide a usable public icon endpoint:

```sh
kubectl -n media exec deployment/radarr -- \
  curl -sS -o /dev/null -w '%{http_code}' \
  http://127.0.0.1:7878/Content/Images/logo.svg
```

It returned `500`. The Authentik application entries therefore use the official
upstream Radarr and Sonarr logo URLs.

To retain access while moving from the shared group to separate groups, the
following command created the groups and copied memberships:

```sh
kubectl -n authentik exec deployment/authentik-worker -- ak shell -c \
  'from authentik.core.models import Group; ...'
```

Observed result:

```text
Migrated 0 member(s) from media-users to radarr-users and sonarr-users.
```

No member belonged to `media-users`; `homelab-admins` continues to authorize
administrators for both applications.

The full media-chart server-side dry run also reported existing immutable PVC
fields, for example:

```text
PersistentVolumeClaim "radarr-config-pvc" is invalid: spec: Forbidden: spec is immutable
```

This is unrelated to the callback change: rendering a bound PVC without its
server-assigned `volumeName` is incompatible with direct `kubectl apply`.
The separately rendered middleware was accepted by the API server.

## Outcome

The media chart no longer creates an ExternalName Service or callback
Ingresses. The authentik chart owns a callback Ingress for each protected host
and routes it to `authentik-server` in the same namespace. Radarr and Sonarr
remain separate authentik applications with separate `radarr-users` and
`sonarr-users` policy bindings, official logos, and NFS-backed application
configuration unchanged.
