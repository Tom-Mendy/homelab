# Backup Procedures

This document defines practical backup steps for this homelab repository
and cluster workloads.

## Scope

- Git repository content (`kubernetes/`, `docs/`, `scripts/`)
- Kubernetes manifests as deployed state (export)
- Persistent data for stateful apps

## Backup policy

- **Config backups**: before every infrastructure change and at least weekly
- **Data backups**: application-dependent (daily for credentials and critical data)
- **Validation**: monthly restore test of at least one backup set

## Important storage rule

Kubernetes persistent data must not use worker-local storage. Standard PVCs
should use the shared Synology NFS-backed `nfs-k8s` StorageClass so workloads can
survive the loss or shutdown of a worker node. S3-compatible storage is reserved
for backups, artifacts, and object data; it is not a general POSIX PVC
replacement.

## 1) Repository backup

The git remote is the primary backup for infrastructure code.

Recommended:

```bash
git status
git add -A
git commit -m "backup: snapshot infrastructure state"
git push
```

Optional archive export:

```bash
mkdir -p backups
tar -czf backups/homelab-$(date +%F).tar.gz \
 kubernetes docs scripts README.md
```

## 2) Kubernetes resource export

Use this to capture current cluster object state (useful before upgrades).

```bash
mkdir -p backups/k8s-$(date +%F)
kubectl get ns -o yaml > backups/k8s-$(date +%F)/namespaces.yaml

for ns in flux-system traefik blocky homepage keel prometheus grafana \
  navidrome vaultwarden forgejo default; do
 kubectl get all,cm,secret,ing,pvc -n "$ns" -o yaml \
  > backups/k8s-$(date +%F)/${ns}.yaml || true
done
```

Notes:

- Secrets exported this way are sensitive; store encrypted.
- This is not a full etcd snapshot.

## 3) Persistent data backup

Stateful services in this repo include at least:

- `vaultwarden`
- `forgejo`
- `grafana`
- `prometheus`
- `navidrome` data PVC
- `trilium`

Recommended approach:

1. Identify PVC/PV used by each service.
2. Use storage-level snapshots or application-native export.
3. Store backups off-cluster (NAS/off-site).

## 4) Pre-maintenance backup checklist

Before a cluster upgrade, GitOps migration, or destructive maintenance:

1. Push all pending Git changes.
2. Export Kubernetes resources.
3. Verify latest backup for critical application data.
4. Confirm restore instructions are available (`docs/disaster-recovery.md`).

## 5) Verification checklist

- Confirm backup files exist and are readable.
- Verify file sizes are non-zero.
- For one service, perform a restore drill in a test namespace or isolated environment.
