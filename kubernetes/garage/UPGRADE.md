# Garage 2.5.0 — BLOCKED maintenance proposal

There is **no active Garage chart under `kubernetes/garage`**. The actual workload
is `job-search-manager/job-search-manager-garage`, rendered from
`kubernetes/job-search-manager/templates/garage.yaml` and the `garage` values in
`kubernetes/job-search-manager/values.yaml`. Those paths are outside this task's
ownership, so no active Garage manifests or versions were modified.

Observed: one replica, replication factor 1, LMDB, a single NFS PVC
`job-search-manager-garage-data`, metadata `/var/lib/garage/meta`, blocks
`/var/lib/garage/data`, default RollingUpdate. Source configuration is
`job-search-manager-garage-config`; rendered configuration uses `GARAGE_RPC_SECRET`
from the chart's `runtimeSecret`. Preserve that exact credential and node identity.

Target verified: `dxflrs/garage:v2.5.0@sha256:677e5b758e4425a325b811c425c026bf35a4bf42f7ddbaa773de3f4fd779a5a5`.
Upstream explicitly forbids downgrading a migrated node. S3 object sync does not
back up node identity, layout, permissions, metadata and every object version.
No warm archive was attempted or represented as recoverable.

## Required source stages (parent / owning agent)

1. Obtain ownership/authorization for the actual chart paths. Add
   `garage.maintenance.enabled: false`; make ONLY the Garage Deployment's
   replicas conditional (0/1), preserving its PVC, configuration and Service.
   Stage explicit RollingUpdate maxSurge=0/maxUnavailable=1 if keeping the
   existing strategy type; changing to Recreate requires a successful applying-
   manager dry-run or a reviewed Deployment-only recreation gate.
2. Prepare old-image resume and target resume changes BEFORE maintenance. Hold
   job-search-manager writers, scheduled consumers and all external S3 clients;
   identify exactly which producers must be paused through their owning source.
   Record non-secret aggregate bucket/key/object/version counts and a bounded
   representative object-content checksum baseline.
3. **Quiesce source commit:** set Garage replicas=0 at OLD image 2.4.1 via GitOps.
   Wait for every Garage Pod to terminate; confirm no other process or Pod can
   write its PVC. If shutdown is unclean, stop and assess before snapshotting.
4. With the node fully OFFLINE, use a narrowly scoped, unexposed backup helper
   mounting the production PVC READ-ONLY and a separate `nfs-k8s` backup PVC.
   Archive the COMPLETE `/var/lib/garage` tree preserving ownership, modes,
   symlinks and node identity, plus the configuration and encrypted external
   escrow of the RPC/application keys. Hash and list the archive. Copy it to an
   independent protected failure domain. Do not tar/rsync live LMDB or blocks.
5. Restore the archive into a NEW scratch NFS PVC and test 2.4.1 first, then 2.5.0
   on a SECOND disposable copy. Default-deny all scratch networking; no public
   ports, ingress or production RPC discovery. Override scratch RPC advertised
   address and use only scratch-local clients. Verify layout, node identity,
   bucket/key permissions and representative complete/versioned object reads.
   Never start a restored node with production gossip connectivity.
6. If backup or rehearsal fails BEFORE production migration, keep originals
   unchanged and resume OLD 2.4.1 promptly through the prepared GitOps source.
   Do not publish the target version while recovery evidence is incomplete.
7. **Resume target commit:** with maintenance false, pin the verified 2.5.0 digest
   in the actual owning values file. Reconcile Garage alone; check node/layout,
   bucket/key permissions, object/version/checksum baseline and S3 operations.
   Lifecycle APIs now require owner keys. `s3_api.public_endpoint` is recommended
   but must reflect the real routed endpoint, not an invented public hostname.
8. If production migration fails, stop the new node. Never downgrade its PVC.
   Restore the pre-upgrade archive into a NEW NFS PVC, reconstruct matching
   configuration/keys, switch the claim via reviewed GitOps source and resume
   OLD 2.4.1 only against that restored directory. Preserve failed/original PVCs
   and explicitly assess writes lost since the maintenance snapshot.

**Current hard blockers:** actual chart path outside ownership; no offline full
node archive; no isolated complete-node restore/migration rehearsal; no verified
independent key/config escrow; consumer pause/resume ownership not established.
No production maintenance, backup Pod mounting Garage, migration or update was run.

Source: <https://git.deuxfleurs.fr/Deuxfleurs/garage/releases/tag/v2.5.0>.
