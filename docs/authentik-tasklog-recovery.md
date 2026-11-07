# Authentik task-log recovery

On 2026-11-07, the Talos preparation restore drill failed while creating
`authentik_tasks_task_task_id_a82f0835_fk_authentik`. Seven task-log rows
referenced two absent tasks. Both the original dump and live database contained
the same invalid references. The logs were dated 2026-08-01, between 07:18 and
07:19 UTC. The exact historical operation that introduced them is unknown.

The diagnostic used the original dump in an isolated local PostgreSQL 17
container with no network and no published ports. The failing foreign-key
creation reproduced twice. Production checks confirmed the same seven rows
with normal and sequential scans. Both tables were logged, the foreign key
was marked validated, its triggers were enabled, and the diagnostic connection
used the normal origin replication role. These observations do not establish
whether constraints were bypassed in the past.

The repair preserved the complete seven original rows in
`homelab_recovery.authentik_tasklog_orphans_20261107`, outside the application
schema. The archive has no task foreign key, because the parents are missing.
Access to its schema and table was revoked from PUBLIC. No parent tasks were
invented and no application constraint was removed or disabled.

The production operation was a single guarded transaction:

1. Acquire short-lived write-conflicting locks on the task and task-log tables
   with a three-second lock timeout and thirty-second statement timeout.
2. Require exactly the seven reviewed row UUIDs, their complete-row
   fingerprints, and two absent parent tasks. Abort if the reviewed set changed.
3. Copy the complete rows into the recovery archive, then remove only those
   exact invalid references from the application task-log table.
4. Require zero remaining orphan logs and verify all seven archived rows still
   match their original fingerprints. Check deferred constraints before commit.

Before production, the transaction was rehearsed against the original dump.
All original post-data objects restored successfully afterwards. Row counts
and complete-row fingerprints matched across the other 229 public tables.
An attempted reinsert of the invalid references failed against the original
foreign key and was rolled back. A repaired dump also passed a complete
restore into another empty isolated database.

Private evidence is stored outside Git on the NixOS workstation at
`/home/tmendy/.local/state/homelab/talos-migration/20261107T102318Z/`:

- `authentik-authentik.dump`: original failing backup, retained unchanged.
- `authentik-before-repair-20261107.dump`: fresh production pre-repair backup.
- `authentik-original-orphan-rows.json`: complete original orphan logs.
- `authentik-reviewed-orphan-repair.sql`: exact guarded one-time transaction.
- `authentik-after-repair-20261107.dump`: fresh complete database backup,
  including the recovery archive.
- `authentik-repair-result.json`: backup checksum and validation results.
- `authentik-production-repair.log` and `authentik-final-restore.log`:
  execution evidence. These files may contain private operational details.

Do not rerun the one-time transaction. It deliberately refuses an empty or
different orphan set. Preserve the archive and its external copy through the
Talos migration. Do not import archived rows into the application table unless
their real parent tasks have been recovered and all constraints can validate.
Reintroducing the old invalid rows is not a useful rollback. A full pre-repair
restore is a separate outage operation and would discard subsequent writes.

Run the reusable read-only check before future Authentik backups and against
restored copies. It fails on orphan logs, a missing or unvalidated foreign key,
disabled foreign-key triggers, or a connection that bypasses normal enforcement:

```sh
kubectl --context kubernetes-admin@cluster.local exec -i \
  -n authentik authentik-postgres-1 -c postgres -- \
  psql -X -v ON_ERROR_STOP=1 -U postgres -d authentik \
  < scripts/check-authentik-tasklog-integrity.sql
```

A successful logical database restore must retain all schemas, including
`homelab_recovery`. Verify schema, data, indexes, constraints, ownership, and
grants. Database roles must exist before restoring their owned objects.
An isolated NOLOGIN role is sufficient to test object ownership and grants;
it does not test production role passwords or login recovery.

This repair does not replace an application login/SSO recovery test or backups
of external credentials and uploaded files. Authentik pods stayed running and
the readiness endpoint at `https://authentik.tom-mendy.com/-/health/ready/`
returned HTTP 200 after the repair.

See the [migration tracker](talos-migration.md) and the upstream
[backup and restore procedure](https://docs.goauthentik.io/sys-mgmt/ops/backup-restore).
