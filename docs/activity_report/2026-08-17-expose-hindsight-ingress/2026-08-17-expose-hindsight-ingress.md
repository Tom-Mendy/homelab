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
