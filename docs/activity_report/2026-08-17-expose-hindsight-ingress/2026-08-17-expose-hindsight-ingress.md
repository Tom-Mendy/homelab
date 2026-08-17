# Expose Hindsight through its internal HTTPS hostname

## Problem

Hindsight was reachable only as the private Kubernetes service
`hindsight.agent.svc.cluster.local:8888`. The requested browser/API entry point
was `https://hindsight.home.tom-mendy.com`.

## Reasoning and commands

Existing applications use a Traefik Ingress with the `web` and `websecure`
entrypoints and the `letsencrypt` certificate resolver. Hindsight already had a
named HTTP service port, so one Ingress routing `/` to that service was enough.
No new Service, storage, authentication layer, or dependency was needed.

The chart was rendered locally:

```console
$ helm lint kubernetes/hindsight
==> Linting kubernetes/hindsight
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed

$ helm template hindsight kubernetes/hindsight >/tmp/hindsight-rendered.yaml
```

The first cluster-side validation could not reach the Kubernetes API from this
environment:

```console
$ kubectl --dry-run=client apply -f /tmp/hindsight-rendered.yaml
error: error validating "/tmp/hindsight-rendered.yaml": failed to download
openapi: Get "https://10.0.0.21:6443/openapi/v2?timeout=32s": dial tcp
10.0.0.21:6443: socket: operation not permitted
```

The rendered Ingress itself was inspected and contained:

```yaml
host: hindsight.home.tom-mendy.com
service:
  name: hindsight
  port:
    name: http
```

The repository storage policy check still passed:

```console
$ ./scripts/check-storage-policy.sh
storage policy ok
```

After the Control Plane was added, Traefik returned `no available server`.
The chart was configured with `ghcr.io/vectorize-io/hindsight-control-plane:0.6.1`,
but the published standalone Control Plane image is available as `0.7.0`.
The fix updates the image tag and adds the existing Authentik forward-auth
pattern for the `homelab-admins` group. The Authentik Outpost callback route is
kept in a separate Ingress so the callback itself is not protected by the
forward-auth middleware.

Validation after the fix:

```console
$ helm lint kubernetes/hindsight
1 chart(s) linted, 0 chart(s) failed

$ helm lint kubernetes/authentik
1 chart(s) linted, 0 chart(s) failed

$ ./scripts/test-helm-chart.sh
=== hindsight ===
OK
...
=== vaultwarden ===
OK

$ ./scripts/check-storage-policy.sh
storage policy ok
```

The rendered manifests contain the `0.7.0` Control Plane image, the
`agent-authentik-hindsight@kubernetescrd` middleware, the Hindsight proxy
provider, and the `/outpost.goauthentik.io` route. Direct cluster verification
was unavailable from this execution environment because access to the API
server at `10.0.0.21:6443` is blocked.

The complete local Helm chart suite passed. Markdown checking was also run;
it reported 136 pre-existing issues in 17 files, mostly line-length warnings.
The new report did not produce a warning.

```console
$ ./scripts/test-helm-chart.sh
=== hindsight ===
OK
...
=== vaultwarden ===
OK

$ rumdl check --fix .
Issues: Found 136 issues in 17/119 files
```

## Final outcome

The Hindsight chart now creates a Traefik HTTPS Ingress for
`hindsight.home.tom-mendy.com`, using the existing Let’s Encrypt resolver and
routing to the existing `hindsight` ClusterIP Service on port 8888. The
hostname must resolve to the internal Traefik address for the URL to work.

Homepage was then updated with a Hindsight shortcut:

```yaml
- Hindsight:
    icon: kubernetes.svg
    href: https://hindsight.home.tom-mendy.com
    description: Agent memory API
```

When opening the shortcut, the API returned `Not Found` at `/`. The API-only
image intentionally has no web interface. The official Hindsight deployment
documentation describes a separate `hindsight-control-plane` image that
provides the UI and proxies requests to the API.

The chart was extended with that Control Plane, keeping the API as an internal
ClusterIP service:

```yaml
image: ghcr.io/vectorize-io/hindsight-control-plane:0.6.1
HINDSIGHT_CP_DATAPLANE_API_URL: http://hindsight.agent.svc.cluster.local:8888
```

The existing Ingress now routes `hindsight.home.tom-mendy.com` to the Control
Plane on port 9999. The local checks passed:

```console
$ helm lint kubernetes/hindsight
1 chart(s) linted, 0 chart(s) failed

$ ./scripts/test-helm-chart.sh
=== hindsight ===
OK
...
=== vaultwarden ===
OK

$ ./scripts/check-storage-policy.sh
storage policy ok
```
