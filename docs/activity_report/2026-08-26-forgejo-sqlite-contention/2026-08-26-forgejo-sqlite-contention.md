# Diagnose and prepare Forgejo SQLite migration

## Problem

Forgejo logged SQL statements lasting from several seconds to almost six
minutes. During the same period, the web interface, Actions pages, and Git
operations became slow or returned HTTP 500 responses.

The suspected migration to PostgreSQL had not happened yet. The goal was to
identify the cause and prepare a safe CloudNativePG migration without changing
the live database during the investigation.

## Reasoning path

The first command used the shell alias from the incident report:

```console
$ k -n forgejo logs forgejo-7cff569bc5-scd67
zsh: command not found: k
```

The equivalent `kubectl` command initially could not reach the cluster from the
sandbox:

```console
$ kubectl -n forgejo logs forgejo-7cff569bc5-scd67 --timestamps --tail=1200
Unable to connect to the server: dial tcp 10.0.0.21:6443: socket:
operation not permitted
```

After read-only network access was allowed, the pod and logs were collected:

```console
$ kubectl -n forgejo get pod forgejo-7cff569bc5-scd67 -o wide
forgejo-7cff569bc5-scd67   1/1   Running   0   9d   10.233.71.49   node3

$ kubectl -n forgejo describe pod forgejo-7cff569bc5-scd67
Restart Count: 0
Events: <none>

$ kubectl -n forgejo top pod forgejo-7cff569bc5-scd67
error: Metrics API not available
```

The effective configuration confirmed that Forgejo still used SQLite:

```console
$ kubectl -n forgejo exec forgejo-7cff569bc5-scd67 -- \
    grep -E '^(DB_TYPE|PATH|HOST|NAME|USER|SSL_MODE|LOG_SQL)' \
    /data/gitea/conf/app.ini
PATH = /data/gitea/gitea.db
DB_TYPE = sqlite3
HOST = localhost:3306
NAME = gitea
USER = root
LOG_SQL = false
SSL_MODE = disable
```

The incident began immediately after a burst of OCI uploads:

```text
12:50:54  POST /v2/tom-mendy/hermes-workspace/blobs/uploads/
12:51:07  first [Slow SQL Query]
12:57:57  last [Slow SQL Query] in the captured interval
```

The log contained 161 slow SQL entries. They included 88 `SELECT` statements,
37 `UPDATE` statements, 25 `INSERT` statements, 8 `BEGIN TRANSACTION`
statements, and 3 `DELETE` statements. The writes were concentrated on
`package_blob_upload`. Examples included:

```text
INSERT INTO package_blob_upload ... - 5m55.689996286s
UPDATE package_blob_upload ... - 5m09.663877345s
SELECT ... FROM user WHERE id=? LIMIT 1 - 33.226248643s
BEGIN TRANSACTION - 28.209893355s
```

The same interval contained OCI requests lasting more than five minutes and
Actions requests returning HTTP 500 after tens of seconds. The `GET
/user/events` requests were treated separately because Forgejo uses that route
for long-polling.

The query plans ruled out a missing index:

```console
$ sqlite3 -readonly /data/gitea/gitea.db \
    'EXPLAIN QUERY PLAN SELECT * FROM user WHERE id=1 LIMIT 1; ...'
SEARCH user USING INTEGER PRIMARY KEY (rowid=?)
SEARCH repository USING INDEX UQE_repository_s (owner_id=? AND lower_name=?)
SEARCH action_runner USING INDEX UQE_action_runner_uuid (uuid=?)
```

The database passed an integrity check:

```console
$ sqlite3 -readonly /data/gitea/gitea.db 'PRAGMA quick_check;'
ok
```

The database and package directory shared the same NFS export:

```console
$ stat -f -c 'filesystem=%T' /data/gitea/gitea.db
filesystem=nfs

$ df -hT /data/gitea/gitea.db
10.0.0.11:/volume1/forgejo   nfs4   3.5T   3.3T   236.8G   93%   /data

$ du -sh /data/gitea/packages
1.2G    /data/gitea/packages
```

After the upload burst ended, the same direct SQLite read took 30–50 ms over
five measurements. This showed that the SQL statements were waiting on SQLite
serialization and NFS-backed file activity, rather than executing slowly
because of their query plans.

## Changes made

The Forgejo chart now contains a validated `database` values block. When its
type is `postgres`, the Deployment reads the CloudNativePG username and
password from the generated application Secret and sets the Forgejo database
environment variables.

A new `forgejo-postgres` local chart creates a one-instance CloudNativePG
cluster with a 20 GiB `nfs-k8s` volume. Flux deploys that release before
Forgejo, and Forgejo depends on the PostgreSQL release. The default remains
`database.type: sqlite3` so this change is non-disruptive until the migration
procedure is run.

The live cutover was not run. The repository is GitOps-managed, and applying a
different database configuration directly to the cluster would create drift
before the change was published.

## Validation results

```console
$ helm lint kubernetes/forgejo
1 chart(s) linted, 0 chart(s) failed

$ helm lint kubernetes/forgejo-postgres
1 chart(s) linted, 0 chart(s) failed

$ ./scripts/test-helm-chart.sh
=== forgejo ===
OK
=== forgejo-postgres ===
OK
...
=== vaultwarden ===
OK

$ ./scripts/check-storage-policy.sh
storage policy ok

$ helm template test kubernetes/forgejo --set database.type=postgres
FORGEJO__database__DB_TYPE=postgres
FORGEJO__database__HOST=forgejo-postgres-rw.forgejo.svc.cluster.local:5432
FORGEJO__database__USER from forgejo-postgres-app/username
FORGEJO__database__PASSWD from forgejo-postgres-app/password
```

The client-side Kubernetes dry run could not validate the Flux resources because
it attempted API discovery and the sandbox blocked the Kubernetes socket:

```console
$ kubectl apply --dry-run=client --validate=false \
    -f kubernetes/flux/cluster/apps/applications.yaml
Unable to connect to the server: dial tcp 10.0.0.21:6443: socket:
operation not permitted
```

## Final outcome

The incident was caused by concurrent Forgejo package-registry uploads
contending on the single SQLite writer path while the database and package
storage used the same NFS export. PostgreSQL should remove the database-wide
SQLite writer bottleneck, but package and Actions file traffic can still put
load on NFS.

The repository is ready for the controlled migration described in the backlog.
That migration still needs a published change, a verified SQLite backup, a
temporary write freeze, `pgloader` output, and post-cutover checks for web,
Git, LFS, Actions, and runner registration.
