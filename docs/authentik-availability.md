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

An unavailable Authentik endpoint also makes forward-auth applications such as
`https://qbittorrent.home.tom-mendy.com/` return HTTP 500. Check Traefik logs
for connection failures to the Authentik service before restarting the
application or changing its authentication settings.

On 2026-10-28, qBittorrent returned HTTP 200 directly, but its public URL
returned HTTP 500. Authentik's database repeatedly lost readiness. PostgreSQL
processes on `node3` were blocked in `nfs_wait_bit_killable`, and a small NFS
file-open probe took 53 to 3,796 ms there versus 0.8 to 2.8 ms on `node2`.
The database had no CPU limit and showed no CPU throttling.

For recovery from this symptom, compare both workers before choosing a
destination. Temporarily cordon the affected worker and gracefully delete
only the Authentik database pod so CloudNativePG recreates it on the healthy
worker with its existing `nfs-k8s` PVC. Wait for the old pod to stop, the new
database to become ready, and Authentik to recover. Never force-delete a
database pod while the old PostgreSQL process might still be running.
Restore the worker's previous scheduling state after the move.

Verify that qBittorrent redirects an unauthenticated request to
`https://authentik.tom-mendy.com/` and that following the redirect reaches the
login page with HTTP 200. This checks the public authentication path without
bypassing access control. Also verify the PVC name and PV binding are unchanged.

Moving the database restores service but does not repair the worker's NFS
client. Follow up with the NFS client recovery procedure in
[Kubernetes storage](kubernetes-storage.md), then rerun the file-access probe
on both workers. Do not pin the database permanently to one worker or disable
health checks to hide the storage latency.

The 2026-10-28 recovery moved `authentik-postgres-1` to `node2` after a clean
PostgreSQL shutdown and restarted the Authentik server there to clear its crash
backoff. The database kept PV `pvc-838dd586-f332-46ea-b676-84a72bbad01b`.
A brand-table query then took 120 ms to plan and 1.2 ms to execute.
`node3` was uncordoned after both replacement pods were assigned to `node2`.
Authentik's readiness endpoint then returned HTTP 200 in 81 ms, its deployment
completed, and the public qBittorrent URL redirected to the canonical Authentik
login flow with a final HTTP 200. The worker's NFS latency still needs repair.
