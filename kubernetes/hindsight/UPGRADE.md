# Hindsight 1.1.0 preparation — NOT deployment approval

The files in `maintenance/` are **inactive values overlays**. Flux reads only
`values.yaml`. Active images remain API 0.10.2 and control plane 0.10.3.
The default maintenance flag is false; rendering remains unchanged.

## Evidence and remaining gates

Restricted evidence: `/opt/data/maintenance-snapshots/resume-stateful/`.
A consistent `pg_dump -Fc` of embedded PG 18.1 succeeded. Its archive was actually
restored with `pg_restore --exit-on-error` into an isolated PG18/vector 0.8.1 Pod
on a new `nfs-k8s` PVC: 25 application tables, all four extensions present.
No active PostgreSQL directory was copied. Scratch restore omitted roles/ACLs;
this is database recovery evidence, NOT an Alembic or application recovery test.
The dump is on the same NAS failure domain and is not an independent backup.

**Do not activate the upgrade until all gates pass:**

1. Rehearse the target API's pg0/Alembic startup against a second restored copy,
   isolated from production integrations. Check schema revision, bank/memory
   counts and representative recall; test retain/reflect only on scratch data.
   This target-image migration rehearsal has NOT been performed.
2. Preserve configuration, database ownership/roles and pg0 bootstrap credential
   recovery in an approved encrypted escrow. Logical scratch restore alone does
   not prove the original pg0 identity/configuration can be reconstructed.
3. Prepare both an old-version resume commit and the target resume commit before
   quiescing. Merge `01-quiesce.values.yaml` into active values via GitOps;
   wait for BOTH Deployments to have zero Pods, including terminating Pods.
4. Take a fresh consistent logical dump and, only after clean PostgreSQL shutdown,
   an optional complete offline PVC archive/snapshot. Preserve original storage;
   validate the final backup and copy it to an independent protected location.
5. Merge `02-upgrade.values.yaml` into active values and reconcile just Hindsight.
   API already uses Recreate. Do not advance another stateful service until
   `/health`, control-plane `/api/health`, bank/memory counts, recall/retain/reflect
   and the authenticated UI have been verified. Parent owns public-route checks.
6. Before target migration, an old-image resume is possible. After migration,
   rollback is restore-based: stop both components; restore into a NEW NFS PVC,
   reconstruct roles/configuration and switch the claim in reviewed GitOps source
   before starting old images. Never overwrite the original PVC or downgrade
   against a migrated data directory. Account for writes since the backup.

## Upstream

- <https://github.com/vectorize-io/hindsight/releases/tag/v0.10.3>
- <https://github.com/vectorize-io/hindsight/releases/tag/v1.0.0>
- <https://github.com/vectorize-io/hindsight/releases/tag/v1.1.0>
- <https://github.com/vectorize-io/hindsight/blob/v1.1.0/hindsight-api-slim/hindsight_api/migrations.py>

The API and control plane must be upgraded together. The 1.0 tag-scoped caller
restrictions require integration verification; reverting an image does not undo
Alembic migrations. The target API digest was rechecked in the official registry.
