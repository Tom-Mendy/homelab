# Navidrome

Navidrome reserves 500m CPU and 1Gi memory. CPU and memory limits are omitted
so scans can use spare node capacity. These requests fit either worker;
the music library and application data remain on Synology NFS.

Resource requests improve scheduling and CPU allocation under contention.
They do not fix database latency or stale library paths. Before increasing
resources, inspect scan logs, cgroup throttling and memory events.

After renaming music files, refresh the library with:

```sh
kubectl -n navidrome exec deployment/navidrome -- /app/navidrome scan --full
```

Wait for `Scanner: Finished scanning all libraries`. Database timeouts during
scans require checking Synology NFS and database contention, even when CPU
and memory are unrestricted. Keep persistent data on shared storage.

Deploy resource changes through the Flux-managed chart in Git. A direct
Deployment patch is temporary because Flux corrects drift.
