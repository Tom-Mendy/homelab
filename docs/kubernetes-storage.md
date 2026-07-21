# Kubernetes Storage

## Standard

Use `nfs-k8s` for standard Kubernetes PVCs.

The backing store is the Synology NFS export:

- Server: `10.0.0.11`
- Export: `/volume1/k8s`
- StorageClass: `nfs-k8s`
- Reclaim policy: `Retain`

The NFS provisioner creates one subdirectory per PVC under `/volume1/k8s`.
This keeps persistent data independent from worker node lifecycle, so workloads
can reschedule when `node2` or `node3` is powered off.

Do not use `local-path` for Kubernetes workloads.

Some legacy PVCs still use `local-path` while they are being migrated. Their
manifests are listed in `scripts/storage-policy-local-path-allowlist.txt`; remove
each entry in the same change that migrates that workload to `nfs-k8s`.

## Object storage

S3-compatible storage is appropriate for backups, artifacts, exports, and object
data. It is not a general replacement for POSIX PVCs because most workloads in
this repository expect a filesystem.

## Migrating an existing local-path PVC

Migrate one workload at a time.

1. Confirm the current PVC and workload:

   ```bash
   kubectl -n <namespace> get deploy,pod,pvc -o wide
   ```

2. Scale the workload down:

   ```bash
   kubectl -n <namespace> scale deploy/<deployment> --replicas=0
   ```

3. Create a temporary PVC using `nfs-k8s`.

4. Start a temporary copy pod that mounts both the old PVC and the temporary NFS
   PVC, then copy with `rsync -aHAX --numeric-ids`.

5. Delete the old `local-path` PVC only after the copy has completed and been
   checked.

6. Create the replacement PVC with the original claim name and
   `storageClassName: nfs-k8s`, or let the updated Helm chart recreate it.

7. Scale the workload back up and verify application health.

8. Remove any old local-path PV and node-local directory only after the
   replacement is confirmed healthy.

## Rebuilding a cluster with existing nfs-k8s data

When rebuilding the cluster, do not let the NFS provisioner create fresh PVC
directories for workloads that already have data under `/volume1/k8s`.

Before the rebuild, record the binding identity:

```bash
kubectl get pvc -A \
  -o custom-columns='NS:.metadata.namespace,PVC:.metadata.name,SC:.spec.storageClassName,VOLUME:.spec.volumeName'
kubectl get pv \
  -o custom-columns='PV:.metadata.name,SC:.spec.storageClassName,SERVER:.spec.nfs.server,PATH:.spec.nfs.path,CLAIM:.spec.claimRef.namespace/.spec.claimRef.name'
```

On the rebuilt cluster, recreate a static NFS PV for each existing dynamic
`nfs-k8s` path, then recreate the matching PVC with the same namespace, PVC
name, and `volumeName`. The Kubernetes object UID will change; the important
identity is the PV/PVC name pair and the NFS path.

## Draining a node with single-instance CloudNativePG

Some homelab PostgreSQL clusters intentionally run as a single CloudNativePG
instance. Their PDBs block normal eviction because there is no standby instance.

For a planned Talos maintenance window, accept downtime for those applications
instead of adding temporary database replicas:

```bash
kubectl get clusters.postgresql.cnpg.io -A -o wide
kubectl get pdb -A -o wide
kubectl drain node2 \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --disable-eviction
kubectl get pods -n authentik -o wide
kubectl get pods -n infisical -o wide
kubectl get clusters.postgresql.cnpg.io -A -o wide
```

Use `--disable-eviction` only during the maintenance window. It bypasses PDB
protection, so Authentik and Infisical may be unavailable while their database
pods restart on another schedulable node.

## Priority

Migrate in this order:

1. Traefik
2. Grafana
3. OpenWebUI
4. Ollama
5. Navidrome data
6. Media config PVCs
7. SparkyFitness PVCs
