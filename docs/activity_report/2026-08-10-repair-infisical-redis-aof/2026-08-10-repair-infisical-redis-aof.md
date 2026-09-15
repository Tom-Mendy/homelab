# Repair Infisical Redis AOF corruption

Date: 2026-08-10

## Problem

Infisical could not become ready because its Redis dependency was in a
`CrashLoopBackOff`. PostgreSQL and the Infisical operator were running, but the
Infisical application restarted repeatedly and all operator-managed
connections, authentications, and static secret synchronizations reported
`False`.

Both Infisical data PVCs were already compliant with the repository storage
policy and used the shared `nfs-k8s` storage class.

## Investigation and reasoning

The pod logs were checked before changing the cluster. Redis loaded its base
RDB successfully, including 21,669 keys, and then rejected the incremental AOF:

```console
$ kubectl logs -n infisical redis-master-0
Bad file format reading the append only file appendonly.aof.73.incr.aof:
make a backup of your AOF file, then use ./redis-check-aof --fix <filename.manifest>
```

Infisical's logs showed the downstream symptom rather than a separate fault:

```console
$ kubectl logs -n infisical deployment/infisical-infisical-standalone-infisical
connect ECONNREFUSED 10.233.10.99:6379
FastifyError: fastify-plugin: Plugin did not start in time
```

The PVC check confirmed that repairing the existing data would not introduce
worker-local storage:

```console
$ kubectl get pvc -n infisical
NAME                        STATUS   CAPACITY   ACCESS MODES   STORAGECLASS
infisical-postgres-1        Bound    10Gi       RWO            nfs-k8s
redis-data-redis-master-0   Bound    5Gi        RWO            nfs-k8s
```

An initial command from the restricted execution environment failed before it
reached Kubernetes. It was retried with the required cluster network access:

```console
$ kubectl scale statefulset redis-master -n infisical --replicas=0
Unable to connect to the server:
dial tcp 10.0.0.21:6443: socket: operation not permitted
```

Redis was then scaled to zero to prevent concurrent access. A temporary pod
using the same Redis image mounted `redis-data-redis-master-0` at `/data`. It
showed the multipart AOF files:

```console
$ kubectl exec -n infisical redis-aof-repair -- \
    find /data -maxdepth 3 -type f -printf '%p\t%s bytes\n'
/data/appendonlydir/appendonly.aof.73.incr.aof  43576103 bytes
/data/appendonlydir/appendonly.aof.73.base.rdb  13569749 bytes
/data/appendonlydir/appendonly.aof.manifest    92 bytes
```

Before repair, all three files were copied to the following recoverable path on
the NFS PVC:

```text
/data/aof-repair-backup-20260810T000000Z/
```

Their SHA-256 hashes were recorded:

```text
dea465101a8e9ae29b9ca04ea737d7de2d90b687075bca3aa7f481a6fb8105b4  appendonly.aof.73.base.rdb
8abdf7884b3c5e6c2baa1ab4c57ccb868714eacef76fa057d6c59fe2120a08b2  appendonly.aof.73.incr.aof
8538fe35f58022b9403df182f9edfad542543e85d1753ec8e73ac03097d04c55  appendonly.aof.manifest
```

## Repair

The Redis-provided repair utility was run against the multipart manifest:

```console
$ printf 'y\n' | redis-check-aof --fix /data/appendonlydir/appendonly.aof.manifest
[info] 21669 keys read
BASE AOF appendonly.aof.73.base.rdb is valid
AOF appendonly.aof.73.incr.aof format error
AOF analyzed: filename=appendonly.aof.73.incr.aof, size=43576103,
ok_up_to=43521971, ok_up_to_line=3608106, diff=54132
Successfully truncated AOF appendonly.aof.73.incr.aof
All AOF files and manifest are valid
```

The utility removed only the invalid 54,132-byte tail. A second read-only check
reported `diff=0` and confirmed that the base AOF, incremental AOF, and manifest
were valid. The temporary repair pod was deleted, Redis was restored to one
replica, and the operator deployment was restarted to force immediate
reconciliation of statuses left stale by the outage.

## Final outcome

Redis accepted the repaired AOF and answered its protocol health check:

```console
$ kubectl exec -n infisical redis-master-0 -- redis-cli ping
PONG
```

The externally routed Infisical status endpoint also recovered:

```console
$ curl -fsS https://infisical.home.tom-mendy.com/api/status
{"message":"Ok","redisConfigured":true,...}
```

The final workload state was:

```console
$ kubectl get pods -n infisical
NAME                                                       READY   STATUS    RESTARTS
infisical-infisical-standalone-infisical-76497d655-gsccv   1/1     Running   5
infisical-postgres-1                                       1/1     Running   0
redis-master-0                                             1/1     Running   0
```

All nine `InfisicalConnection` resources became `Ready=True`, all nine
`InfisicalAuth` resources became `Ready=True`, and all nine
`InfisicalStaticSecret` resources became `Synced=True`. No Helm or Kubernetes
manifest change was required; the only persistent cluster mutation was the
validated AOF repair, with its pre-repair backup retained on shared NFS.
