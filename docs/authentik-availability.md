# Authentik availability

If `https://authentik.tom-mendy.com/` returns HTTP 503 with `no available
server`, check whether the Authentik server has a ready endpoint:

```sh
kubectl -n authentik get pods -o wide
kubectl -n authentik get endpointslices -l kubernetes.io/service-name=authentik-server
kubectl -n authentik get events --sort-by=.lastTimestamp
```

On 2026-10-22, the server had restarted 99 times because startup and liveness
checks exceeded the chart's three-second timeout. Internal health requests
returned HTTP 200 after 6 to 11 seconds. Database connections and `SELECT 1`
were fast, but initial query planning sometimes took over two seconds.
The source of that latency remains unresolved.

The server probes now allow 30 seconds per request and run every 30 seconds.
Startup still allows approximately ten minutes. Health checks remain enabled.
These values are recorded in `kubernetes/authentik/values.yaml` and were also
applied as inline `spec.values.server` overrides on the live Flux HelmRelease
to recover service before the repository change is published. Remove those
inline probe overrides after Flux has loaded the updated values ConfigMap,
so future probe settings have one source. Keep PostgreSQL on `nfs-k8s`;
moving the database to worker-local storage is not a recovery procedure.

Verify the deployment completes and the public login page returns HTTP 200:

```sh
kubectl -n authentik rollout status deployment/authentik-server
curl --fail --location --max-time 60 --output /dev/null \
  --write-out '%{http_code}\n' https://authentik.tom-mendy.com/
```
