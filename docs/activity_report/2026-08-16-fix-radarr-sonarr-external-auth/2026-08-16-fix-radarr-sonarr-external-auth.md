# Fix Radarr and Sonarr External Authentication

## Problem

After completing the Authentik login flow, both Radarr and Sonarr returned an
HTTP error containing this exception:

```text
Unable to cast object of type 'DryIoc.ScopedItemException' to type
'Microsoft.AspNetCore.Authorization.IAuthorizationHandler'.
```

The Authentik embedded outpost was healthy and redirected requests correctly,
so the failure occurred inside the two Servarr applications.

## Investigation and reasoning

The application logs reproduced the same exception for `GET /` in Radarr
`6.1.1.10360` and Sonarr `4.0.17.2952`:

```sh
kubectl -n media logs deployment/radarr --since=30m
kubectl -n media logs deployment/sonarr --since=30m
```

Their active configuration contained:

```xml
<AuthenticationMethod>None</AuthenticationMethod>
<AuthenticationRequired>Disabled</AuthenticationRequired>
```

The official Radarr and Sonarr sources define `External` as a supported
authentication method. They do not define `Disabled` as an
`AuthenticationRequiredType`; `Enabled` is supported by both versions. The
invalid enum value caused dependency injection to fail while constructing the
UI authorization handler.

The existing init containers edited the persistent XML configuration with
`sed`. They were replaced with the applications' native environment
configuration, which has priority over `config.xml`:

```text
RADARR__AUTH__METHOD=External
RADARR__AUTH__REQUIRED=Enabled
SONARR__AUTH__METHOD=External
SONARR__AUTH__REQUIRED=Enabled
```

Traefik and Authentik remain responsible for authenticating external users.
Both application Services remain internal `ClusterIP` Services.

## Commands and results

The chart rendered successfully:

```sh
helm template media kubernetes/media \
  --namespace media > /tmp/media-rendered-auth-fix.yaml
```

A server-side dry run of the entire rendered chart reported immutable
`volumeName` differences on already-bound PVCs. This was unrelated to the
authentication change and confirmed why the rollout should be limited to the
two Deployments:

```text
PersistentVolumeClaim is invalid: spec is immutable after creation
```

Only the affected Deployments were then selected and validated:

```sh
yq 'select(.kind == "Deployment" and
  (.metadata.name == "radarr" or .metadata.name == "sonarr"))' \
  /tmp/media-rendered-auth-fix.yaml > /tmp/media-auth-deployments.yaml
kubectl apply --dry-run=server -f /tmp/media-auth-deployments.yaml
```

Result:

```text
deployment.apps/radarr configured (server dry run)
deployment.apps/sonarr configured (server dry run)
```

Both Deployments were applied and rolled out:

```sh
kubectl apply -f /tmp/media-auth-deployments.yaml
kubectl -n media rollout status deployment/radarr --timeout=180s
kubectl -n media rollout status deployment/sonarr --timeout=180s
```

Strategic merge initially retained the old init containers. They were removed
explicitly from the live Deployments, matching the Helm chart, and both
rollouts completed again:

```sh
kubectl -n media patch deployment radarr --type=json \
  -p='[{"op":"remove","path":"/spec/template/spec/initContainers"}]'
kubectl -n media patch deployment sonarr --type=json \
  -p='[{"op":"remove","path":"/spec/template/spec/initContainers"}]'
```

The final pods were ready and had no init containers:

```text
radarr ready=true init=
sonarr ready=true init=
```

Internal and public HTTP checks returned the expected status codes:

```text
radarr internal=200
sonarr internal=200
radarr public=302
sonarr public=302
```

The final pod logs contained no `DryIoc.ScopedItemException`,
`InvalidCastException`, or failed root request.

## Final outcome

Radarr and Sonarr now use their supported external-authentication mode. Users
authenticate once through Authentik and reach the applications without a
second application password. The invalid authorization configuration and its
DryIoc exception are gone.
