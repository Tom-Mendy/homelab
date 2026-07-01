# Enable Infisical Internal IP Connections

## Problem

Creating Kubernetes Auth in Infisical failed when the Kubernetes API endpoint
used an internal address:

```text
Bad Request
Local IPs not allowed as URL.
Request ID: req-HO8JspDGt0uGeS
```

The cluster is private and Infisical needs to call the Kubernetes API during
Kubernetes Auth token review. The attempted configuration used:

```text
Kubernetes Host: https://kubernetes.default.svc:443
Allowed Namespaces: traefik
Allowed Service Account Names: traefik-infisical-sync
```

## Reasoning path

The Infisical standalone Helm chart supports container environment variables
through `infisical.extraEnv`. The self-hosted Infisical backend can be allowed
to reach internal/private addresses by setting:

```text
ALLOW_INTERNAL_IP_CONNECTIONS=true
```

This is acceptable for this homelab because Infisical is private and used as an
admin-only internal service. The tradeoff is that Infisical can now make backend
requests to private network destinations, so Infisical must remain protected.

## Commands and results

Inspect Infisical chart values to confirm the correct values path:

```sh
helm show values infisical-standalone \
  --repo https://dl.cloudsmith.io/public/infisical/helm-charts/helm/charts/
```

Relevant output:

```text
infisical:
  extraEnv: []
```

Validate the repository storage policy:

```sh
./scripts/check-storage-policy.sh
```

Result:

```text
storage policy ok
```

Render the upstream Infisical chart with the repository values:

```sh
helm template infisical infisical-standalone \
  --repo https://dl.cloudsmith.io/public/infisical/helm-charts/helm/charts/ \
  -f kubernetes/infisical/infisical-values.yaml
```

Relevant output:

```yaml
env:
  - name: DB_CONNECTION_URI
    valueFrom:
      secretKeyRef:
        name: infisical-postgres-app
        key: uri
  - name: REDIS_URL
    value: redis://default:@redis-master:6379
  - name: ALLOW_INTERNAL_IP_CONNECTIONS
    value: "true"
```

## Final outcome

`kubernetes/infisical/infisical-values.yaml` now sets:

```yaml
infisical:
  extraEnv:
    - name: ALLOW_INTERNAL_IP_CONNECTIONS
      value: "true"
```

After Argo CD syncs the `infisical` application, retry Kubernetes Auth creation
with:

```text
Kubernetes Host: https://kubernetes.default.svc:443
Allowed Namespaces: traefik
Allowed Service Account Names: traefik-infisical-sync
```
