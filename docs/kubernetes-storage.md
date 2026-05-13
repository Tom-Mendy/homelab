# Kubernetes Storage

## Standard

Use `nfs-k8s` for standard Kubernetes PVCs.

The backing store is the Synology NFS export:

- Server: `192.168.1.1`
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

## Priority

Migrate in this order:

1. Traefik
2. Grafana
3. OpenWebUI
4. Ollama
5. Navidrome data
6. Media config PVCs
7. SparkyFitness PVCs
