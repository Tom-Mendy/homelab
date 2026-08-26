# Forgejo SQLite To CloudNativePG Migration Backlog

## Implementation status

The non-disruptive preparation is complete. The repository now renders a
dedicated CloudNativePG cluster and Forgejo can select PostgreSQL through the
`database.type` value. The live cutover remains pending because it requires a
published GitOps change, a maintenance window, and a verified SQLite backup.

## Goal

Plan the future migration of Forgejo from the current SQLite database on
`/data/gitea/gitea.db` to a CloudNativePG PostgreSQL cluster.

This backlog is planning only. Do not run this during the runner scale-out
change.

## Current State

- Forgejo runs as one pod in namespace `forgejo`.
- Forgejo data is mounted from the NFS-backed `forgejo-data-pvc`.
- SQLite database path is expected under `/data/gitea/gitea.db`.
- CloudNativePG is already used by `infisical-postgres` and
  `authentik-postgres`.
- Existing CNPG app clusters use:
  - PostgreSQL image `ghcr.io/cloudnative-pg/postgresql:17`
  - storage class `nfs-k8s`
  - one instance
  - CNPG-generated application secret

## Target Shape

Create a new local chart, `kubernetes/forgejo-postgres`, following the existing
CNPG chart pattern:

```yaml
namespace: forgejo

cluster:
  name: forgejo-postgres
  instances: 1
  imageName: ghcr.io/cloudnative-pg/postgresql:17
  storage:
    size: 20Gi
    storageClass: nfs-k8s
  database: forgejo
  owner: forgejo
```

Create an Argo CD app for `forgejo-postgres` before the Forgejo app sync wave.

Extend the Forgejo chart with a `database` values block:

```yaml
database:
  type: sqlite3
  host: forgejo-postgres-rw.forgejo.svc.cluster.local:5432
  name: forgejo
  sslMode: disable
  secretName: forgejo-postgres-app
```

When `database.type` is `postgres`, the Forgejo Deployment should set:

- `FORGEJO__database__DB_TYPE=postgres`
- `FORGEJO__database__HOST`
- `FORGEJO__database__NAME`
- `FORGEJO__database__SSL_MODE`
- `FORGEJO__database__USER` from CNPG secret key `username`
- `FORGEJO__database__PASSWD` from CNPG secret key `password`

## Migration Procedure

1. Prepare and review all manifests.
   - Add `forgejo-postgres` chart.
   - Add Argo CD app.
   - Add Forgejo DB values support.
   - Keep `database.type: sqlite3`.

2. Stop writes.
   - Scale Forgejo runners to zero.
   - Scale Forgejo to zero.
   - Confirm no user-facing writes are active.

3. Back up data.
   - Back up the Synology NFS path `/volume1/forgejo`.
   - Create a SQLite backup with `.backup`.
   - Optionally run `forgejo dump` as secondary evidence, not as the primary
     restore path.

4. Create PostgreSQL target.
   - Sync `forgejo-postgres`.
   - Wait for `forgejo-postgres-rw` service.
   - Confirm CNPG generated `forgejo-postgres-app`.

5. Migrate SQLite to PostgreSQL.
   - Run `pgloader` from a temporary migration pod or admin environment.
   - Source is the copied SQLite database.
   - Target is the CNPG application database.
   - Capture all logs in an activity report.

6. Flip Forgejo to PostgreSQL.
   - Set `database.type: postgres`.
   - Sync Forgejo.
   - Let Forgejo run normal DB migrations.

7. Verify.
   - Web login works.
   - Repository list loads.
   - Git SSH fetch works.
   - LFS works.
   - Actions queue works.
   - Runner registration still works.

8. Re-enable runners.
   - Scale runner Deployments back to normal.
   - Trigger CI workflow.

## Rollback

Rollback is allowed only while the old SQLite database is still untouched.

1. Scale Forgejo and runners down.
2. Set `database.type: sqlite3`.
3. Sync Forgejo.
4. Scale Forgejo up.
5. Verify web, Git SSH, and Actions.
6. Keep PostgreSQL cluster for investigation until the rollback window ends.

## Validation

Before migration PR is merged:

```sh
helm template test kubernetes/forgejo
helm template test kubernetes/forgejo-postgres
./scripts/test-helm-chart.sh
./scripts/check-storage-policy.sh
rumdl check --fix .
```

During live migration:

- write an activity report under `docs/activity_report/`;
- include failed commands;
- include SQLite backup command output;
- include CNPG readiness output;
- include `pgloader` output;
- include post-cutover Forgejo checks.

## References

- Forgejo database preparation:
  <https://forgejo.org/docs/next/admin/database-preparation/>
- Forgejo CLI dump and migrate commands:
  <https://forgejo.org/docs/latest/admin/command-line/>
- pgloader SQLite to PostgreSQL:
  <https://pgloader.io/>
- Existing repo CNPG patterns:
  `kubernetes/infisical-postgres` and `kubernetes/authentik-postgres`
