# Diagnose Radarr and Sonarr SQLite failures

## Problem

The media automation interface could not add a film for automatic download.
The suspected cause was the recent qBittorrent migration to the NymVPN sidecar.

## Reasoning and Commands

The first checks targeted the qBittorrent network path and the ARR application
logs:

```sh
kubectl -n media get deploy,pods,svc,endpoints,pvc -o wide
kubectl -n media logs deploy/qbittorrent -c nymvpn --tail=160
kubectl -n media exec deploy/radarr -- \
  sh -c 'wget -qSO- --timeout=5 http://qbittorrent:8080/ -O /dev/null'
kubectl -n media exec deploy/sonarr -- \
  sh -c 'wget -qSO- --timeout=5 http://qbittorrent:8080/ -O /dev/null'
```

Both ARR pods received HTTP 200 from qBittorrent. Sonarr logs also showed
successful download submissions after the NymVPN migration. Therefore the VPN
was not the current cause of the failure.

Radarr instead logged this error repeatedly:

```text
System.Data.SQLite.SQLiteException: constraint failed
UNIQUE constraint failed: Commands.Id
```

Sonarr logged intermittent `database is locked` errors. The HelmRelease was
suspended and both deployments were stopped before inspecting their SQLite
databases:

```sh
kubectl -n flux-system patch helmrelease media --type=merge \
  -p '{"spec":{"suspend":true}}'
kubectl -n media scale deployment/radarr deployment/sonarr --replicas=0
```

The first attempt to suspend with `kubectl -n flux-system suspend helmrelease`
failed because this environment treats `suspend` as a plugin command. The
`flux` CLI was also not installed. Patching `spec.suspend` was the compatible
fallback.

Complete `/config` archives were written to the respective NFS PVCs before
any database work:

```text
/radarr/.maintenance-backups/radarr-2026-08-16T2105CEST.tar.gz
/sonarr/.maintenance-backups/sonarr-2026-08-16T2105CEST.tar.gz
```

SQLite integrity checks reported:

```text
radarr: Freelist corruption and Commands B-tree row IDs out of order
sonarr: ok
```

Radarr's `Commands` table had 2,645 rows, with IDs through 427992 while its
SQLite sequence was only 427911. This explains the duplicate-ID failure when
Radarr tried to queue a new command.

A separate copy was rebuilt with `VACUUM INTO`. Its only remaining corruption
was the `Commands` table. Recreating that disposable command queue in the copy
produced the following result:

```text
integrity_check: ok
commands_count: 0
movies_count: 6
download_clients_count: 1
```

## Final Recovery and Outcome

After explicit approval, Radarr was stopped once more and a final complete NFS
archive was created:

```text
/radarr/.maintenance-backups/radarr-2026-08-16T2120CEST.tar.gz
SHA-256: ed13c808b98bc840191a94bcd1be8d90cee43f4ac6ae2365cbf9bc3254a9dc80
```

The corrupted production database was atomically renamed to
`radarr.db.corrupt-2026-08-16T2120CEST`. The validated rebuilt database then
took its place as `radarr.db`. The replacement preserved six movies and one
download client, reset only the disposable `Commands` queue, and passed
`PRAGMA integrity_check`.

On the first recovered startup, the housekeeping task exposed an independent
corruption in the non-business `logs.db` database:

```text
HousekeepingService: Error running housekeeping task: TrimLogDatabase
database disk image is malformed
```

`logs.db` was preserved as `logs.db.corrupt-2026-08-16T2125CEST`; its WAL and
SHM files were removed while Radarr was stopped. Radarr recreated a clean log
database on the next startup. Movie data, settings, and qBittorrent settings
were not modified.

Final checks showed:

```text
radarr_api=200
http://qbittorrent:8080/ 200
http://qbittorrent.media.svc.cluster.local:8080/ 200
deployment "radarr" successfully rolled out
suspended=false
```

No `UNIQUE constraint`, `database is locked`, `database disk image is
malformed`, or `SQLiteException` entries were present in the post-recovery
Radarr logs. Flux was resumed and Radarr returned to `1/1 Available`.

Storage policy verification also passed:

```text
storage policy ok
```
