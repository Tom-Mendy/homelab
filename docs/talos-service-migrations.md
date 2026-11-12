# Remaining Talos service migrations

Execution continued on 2026-11-11. Application versions and optional-load
maintenance holds remain fixed. The migration branch is separate from main;
Ubuntu retains its original pinned Git source while each Talos revision is
reviewed and explicitly selected.

| Service | State | Data and routing |
| --- | --- | --- |
| Portfolio | Migrated and observed | Public Pangolin route to Talos .70 |
| Cinny | Migrated and observed | Public chat route to Talos .70; Matrix backend remains Ubuntu |
| Navidrome | Migrated and observed | Single writer on existing Synology paths; Ubuntu ingress bridge retained |
| SearXNG | Migrated and observed | NymVPN state kept on the same Synology NFS path; Ubuntu ingress and in-cluster consumer bridges reach Talos .70 |
| Homepage | Migrated and observed | Stateless config on Talos; Ubuntu ingress bridges to Talos .70 |
| Radarr | Migrated and observed | Existing Synology config and media paths mounted by Talos; Ubuntu ingress bridges to Talos .70 |
| Sonarr | Migrated and observed | Existing Synology config, downloads, and series paths mounted by Talos; Ubuntu ingress bridges to Talos .70 |
| Prowlarr | Migrated and observed | Existing Synology config on Talos; Ubuntu ingress bridges to Talos .70; Radarr and Sonarr app connections validated |
| qBittorrent | Migrated and observed | Existing config, NymVPN state, and downloads remain on Synology NFS; Ubuntu HTTPS ingress bridges to Talos .70 |
| NZBGet | Migrated and observed | Existing config, NymVPN state, and downloads remain on Synology NFS; Ubuntu HTTPS ingress bridges to Talos .70 |
| Atuin | Migrated, observed, and client sync validated | PostgreSQL and app on Talos; Ubuntu HTTPS bridge retained |
| Grafana | Migrated, observed, and browser OIDC/dashboard validation confirmed | SQLite on Talos; Prometheus source is Talos; Ubuntu ingress bridge retained |
| Infisical | Migrated, observed, and secret-sync validated | App v0.166.5 retained; 795-table PostgreSQL restore on nfs-k8s; Redis reuses its original Synology NFS directory; Ubuntu ingress bridge retained |
| Harbor | Migrated and observed | Harbor v2.15.4 and chart 1.19.4 retained; five existing Synology NFS paths rebound; Talos-specific Infisical auth; Ubuntu HTTPS ingress bridges to Talos `.70` |
| Hindsight | Migrated and observed | Exact production image digests and existing embedded PostgreSQL directory on Synology NFS; Ubuntu HTTPS ingress bridges to Talos `.70`; Ubuntu Authentik outpost remains active |
| Vaultwarden | Migrated and user validated | PostgreSQL on Talos; Ubuntu SQLite writer stopped; Ubuntu ingress bridges to Talos .70 |
| MatrixRTC | LiveKit/JWT component migrated, observed, and real Element call validated | Talos `.74`; Ubuntu Services and public ingress bridge to Talos; Newt remains Ubuntu |
| Tuwunel | Migrated, observed, and user validated | Single writer on existing Synology NFS paths; Ubuntu ingress and ClusterIP bridge to Talos `.75` |
| Job Search Manager | Cutover prepared; deferred for Authentik outpost configuration | Ubuntu app and Garage restored; final PostgreSQL restore and Garage data verified on Talos, where the app and Garage remain stopped |

Hindsight now runs on Talos with the exact production API and control-plane
image digests. Its pre-bound Retain PV uses the same Synology NFS directory as
the Ubuntu claim; the Ubuntu Deployments were stopped before either Talos Pod
mounted it. The Ubuntu HelmRelease remains suspended, its Deployments stay at
zero, and its HTTPS Ingress bridges to Talos while the more-specific Ubuntu
Authentik outpost route remains in place. Six samples over five minutes showed
both Talos Pods Ready with no restarts; the in-Pod API `/health` and control
plane `/api/health` checks returned 200, and direct plus bridged HTTPS returned
the expected redirect to `authentik.tom-mendy.com`. An authenticated UI session
was not available in the preview browser, so browser-side sign-in remains
unverified. Ollama is still stopped on Ubuntu and has not been moved, so
Hindsight inference remains unavailable until that dependency is restored.

For rollback, stop both Talos Deployments and wait for all Pods to exit before
starting the Ubuntu Deployments against the same NFS directory. Restore the
Ubuntu Ingress backend from the private snapshot in
`~/.local/state/homelab/talos-migration/20261111-remaining-services/hindsight/rollback/`.
Never run both clusters' Hindsight API writers at once.

Job Search Manager is currently serving from Ubuntu. The Talos CloudNativePG
operator and target cluster are ready. The final PostgreSQL dump
`postgres-final-20261112T115320Z.sql.gz` passed gzip verification and restored
11 public tables to Talos; its SHA-256 is
`897973c877d52952b8ded148a97c780fd6640dd5b674fafa8475ef397a703764`. Garage
was moved as a single writer onto Talos and read the existing NFS data
successfully: the `job-search-documents` bucket contained 29 objects totaling
4,018,668 bytes, matching the final archive at
`/backups/objects-final-20261112T1154Z`. The application image pulled
successfully and its health endpoint passed on Talos.

The existing Authentik provider remains in single-application mode on the shared
embedded outpost, and the `homelab-admins` application binding remains enabled
with policy engine `ANY`. Its forward-auth endpoint is the provider external-host
path `https://suivi-stage.home.tom-mendy.com/outpost.goauthentik.io/auth/traefik`;
a temporary Talos probe returned HTTP 200 and the Talos Middleware now uses this
endpoint. Browser review confirmed the group restriction was preserved. No
provider or group-policy change was needed.

The service cutover is still deferred. The Ubuntu app, Garage, and scheduled
backups remain available; Ubuntu remains the only active application writer.
Talos retains the restored database and Garage data, while the app and Garage
Deployments remain at zero replicas. A temporary start was reset by Flux before
readiness validation; `/health/ready` returned 503 during that attempt. Diagnose
the readiness dependency, then enable both target Deployments through GitOps. Keep
the Ubuntu public Ingress pointed at the source until target health and
authenticated access pass.

SearXNG now runs on Talos with the same application and NymVPN image digests.
The source Deployment was stopped before the Talos writer started. A read-only
inspection Pod captured the quiesced VPN state (13 files, 245,574 bytes) into
an encrypted Age archive; decryption and gzip/tar integrity checks passed in
memory. Infisical now authenticates the dedicated Talos ServiceAccount through
the Talos API with CA verification, and both synchronized application Secrets
match Ubuntu. NymVPN reports Connected and the application reports Swiss
egress. The unchanged LAN hostname reaches Talos through an Ubuntu
Service/EndpointSlice bridge from Traefik .60 to Talos ingress .70. Direct and
bridged HTTPS, health, route marker, and response body matched during 313
seconds of observation (31 samples). One request immediately after the
Ingress backend patch returned 503 while routing updated; subsequent checks
and the full observation window passed. Ubuntu SearXNG remains at zero
replicas and its HelmRelease remains suspended.

OpenWebUI in the Ubuntu `ollama` namespace still uses the cluster-local URL
`http://searxng.searxng.svc.cluster.local:8080/search`. After the SearXNG
cutover, that URL failed because Kubernetes Service DNS is cluster-scoped. The
Ubuntu Service now has no selector and an EndpointSlice targets Talos ingress
`.70:80`; a second Talos Ingress host rule accepts the unchanged service FQDN.
The actual OpenWebUI pod returned HTTP 200 JSON from its configured URL after
the bridge. Keep this bridge until OpenWebUI moves, then remove the Ubuntu
selectorless Service/EndpointSlice and the internal Talos host rule in the same
reviewed Git change. The original Ubuntu Service selector and port are in the
private rollback snapshot `searxng/source-service-before-internal-bridge.json`.

OpenWebUI remains on Ubuntu. Its Ollama inference Deployment is intentionally
at zero replicas during the GPU maintenance hold, so the Ubuntu ingress returns
503 `no available server` for `/api/tags`. Talos can reach the Talos SearXNG
endpoint, but an OpenWebUI cutover cannot yet pass an end-to-end model check.
Keep inference stopped during the GPU hold; validate the model path after the
GPU worker is available on Talos and before completing the OpenWebUI migration.

Homepage uses the unchanged production image digest and the repository's
services configuration; it has no PVC or external secret dependency. The
Talos response through both `.70` and the retained Ubuntu ingress `.60` matched
the pre-cutover HTTPS body exactly (79,530 bytes; SHA-256
`2256b0053eff37d108337d869aee87d1c2c75ab0efb8c627abb9f60b5bdfc59a`). After
the route switch, Ubuntu's Deployment was scaled to zero while its HelmRelease
remained suspended. Eleven checks over 300.7 seconds returned the expected
Talos route marker and identical body, with no Ubuntu pod and no Talos restart.
OpenWebUI-to-SearXNG connectivity also passed during observation. Roll back by
restoring the Ubuntu Ingress backend from the private snapshot
`homepage/ubuntu-ingress-before-cutover.json` and scaling the Ubuntu Deployment
to one; keep the Talos copy available until the old route is healthy. Remove
the Ubuntu Talos-bridge Service/EndpointSlice only after the hostname no longer
routes through Ubuntu Traefik.

Radarr now runs on Talos with its exact production image digest and current
configuration/database preserved on the same Synology NFS paths. The config
PV is a pre-bound `nfs-k8s` PV to the existing provisioner-managed directory;
download and movie-library PVs point to the existing Synology exports. All
three target PVs use Retain, have no node affinity, and were verified mounted
read-only from node2 before cutover. The image was also pulled on node2 ahead
of downtime. Ubuntu Radarr was stopped before the target Deployment started;
there was no overlapping writer. A stopped-writer snapshot of the active
database, log database, and application config was encrypted and verified; both
SQLite quick checks returned `ok`. Historical `.corrupt-*` files in the source
config directory were left untouched.

Radarr's authenticated route uses the existing per-app Authentik outpost path
on its application hostname; the unauthenticated redirect target remains
`authentik.tom-mendy.com`. Both the direct Talos URL and the existing Ubuntu
ingress returned HTTP 302 through Talos with the `talos-radarr` marker. The
outpost callback returned HTTP 302 from a Talos workload. Radarr's API returned
version 6.4.4.10685, 515 movies, one root folder, one indexer, and five disk
entries. Eleven checks over 301.6 seconds passed with no source Pod and no
target restart. Its two API health warnings are the expected missing
qBittorrent download client while the maintenance profile keeps qBittorrent
stopped; do not thaw it as part of this service cutover. A browser-authenticated
session was not exercised. Rollback by setting the Talos Deployment to zero
and waiting for its Pod to exit, restoring the private Ubuntu Ingress snapshot
and its original Authentik middleware, then scaling Ubuntu Radarr to one. Both
clusters reference the same NFS paths, so never run both copies as writers.

Sonarr now runs on Talos with its exact production image digest. Its config PV
binds the existing provisioner-managed Synology directory; the existing
downloads PVC is shared with Talos Radarr, and the series PV binds the existing
Synology `/volume1/video/Serie` export. These Retain PVs have no node affinity.
Node2 pulled the image and mounted all three paths read-only before the source
was stopped. The stopped-writer encrypted snapshot contains the database,
SQLite WAL/SHM files, log database, and application config; archive decryption
and both SQLite quick checks passed. Ubuntu Sonarr was stopped before Talos
started. The Talos API returned version 4.0.20.3014, 27 series, one root
folder, one indexer, and two disk entries. The same two qBittorrent maintenance
warnings are present. Direct and Ubuntu-bridged HTTPS returned the Talos route
marker and an Authentik redirect, and the outpost callback passed from Talos.
Eleven checks over 301.4 seconds passed without an Ubuntu Pod or Talos restart.
A browser-authenticated session was not exercised. Roll back by setting the
Talos Deployment to zero and waiting for its Pod to exit, restoring the source
Sonarr Ingress snapshot, then scaling Ubuntu Sonarr to one. Do not run both
Sonarr writers against the shared config path.

Prowlarr now runs on Talos using the existing Synology configuration path and
its pinned production image. Its final stopped-writer snapshot is encrypted;
archive decryption and SQLite quick checks for `prowlarr.db` and `logs.db`
passed. Ubuntu was stopped before the Talos writer started. Prowlarr API
`applications/testall` returned two valid connections to Talos Radarr and Sonarr.
Ten checks over 302 seconds passed: the Talos and Ubuntu-bridged HTTPS routes
reached the Talos target, its login page returned successfully, HTTP through
Ubuntu redirected to HTTPS, and the target had no restarts or source Pod.
Prowlarr uses its own login, so no Authentik browser session applies. Its
application redirects to its own HTTP login path; while public traffic still
passes through Ubuntu, Ubuntu Traefik enforces HTTPS. Before moving external
HTTP traffic directly to Talos ingress, enable and validate a Talos-wide
HTTP-to-HTTPS redirect. Roll back by stopping the Talos Deployment, restoring
the source Ingress snapshot, then starting Ubuntu Prowlarr. Never run both
writers against the shared config path. Keep the Ubuntu bridge and suspended
release until traffic no longer uses Ubuntu Traefik.

qBittorrent now runs on Talos with its production image and the stopped-writer
configuration and NymVPN state preserved on their existing Synology NFS paths.
Downloads remain on the shared `/volume1/Downloads` export. The target PVCs use
Retain PVs without node affinity. The source Deployment was stopped before the
Talos writer started; a final encrypted config/VPN-state snapshot passed
decryption and archive integrity checks. The app has an isolated `qbittorrent`
namespace with privileged Pod Security labels because the NymVPN sidecar needs
`NET_ADMIN` and `/dev/net/tun`; the shared `media` namespace remains baseline.

The `media/qbittorrent` DNS name is preserved as an ExternalName alias to the
Talos service so Radarr and Sonarr did not need a configuration change. Their
download-client tests both passed. The existing Ubuntu ingress now bridges
HTTPS traffic to Talos ingress `.70:80`; Authentik challenges are handled on the
Talos route and HTTP traffic continues to redirect to HTTPS at Ubuntu. Ten
checks over 325 seconds passed with the Talos route marker, zero Ubuntu Pods,
zero Talos restarts, and NymVPN ready. The Ubuntu `media` HelmRelease remains
suspended because other media workloads still depend on it.

The Harbor pull secret was copied directly from the working Ubuntu `media`
Secret into Talos after the existing `/harbor/portfolio` credential was denied
access to the `homelab/nymvpn-sidecar` repository. Secret data was not written
to Git or printed. The target secret is not currently synchronized from
Infisical; add a credential with access to the homelab repository in Infisical
before rotating this pull secret or rebuilding Talos. Roll back by stopping
the Talos Deployment first, restoring the Ubuntu ingress backend and its
Authentik middleware, then starting Ubuntu qBittorrent. Both deployments share
the same NFS paths, so never run both as writers. Keep the bridge and Ubuntu
release suspended until external traffic no longer uses Ubuntu Traefik.

NZBGet now runs on Talos with its existing configuration, NymVPN state, and
download directory on Synology NFS. The final stopped-writer snapshot contains
18 files (2 config and 16 VPN-state files); Age decryption and tar/gzip
integrity verification passed. All three target PVs are Retain NFS volumes
without node affinity. The app runs in a dedicated privileged namespace for
the VPN sidecar's `NET_ADMIN` capability and `/dev/net/tun` device. Radarr and
Sonarr have qBittorrent as their only enabled download client, so moving NZBGet
did not change their active download path.

The `media/nzbget` service name is preserved as an ExternalName alias. The
Ubuntu ingress bridges `nzbget.home.tom-mendy.com` to Talos ingress `.70:80`;
the original NZBGet HTTP authentication remains enabled. Direct and bridged
HTTPS returned HTTP 401 with the expected application authentication challenge
and `talos-nzbget` route marker; an authenticated JSON-RPC version request
returned HTTP 200. Eleven checks over 300.6 seconds passed with HTTP-to-HTTPS
redirects at Ubuntu, zero Ubuntu Pods, no Talos restarts, the target GitOps
Kustomization Ready, and NymVPN ready. The Ubuntu `media` HelmRelease remains
suspended for other workloads.

NZBGet uses the existing Harbor pull secret copied into the Talos cluster for
qBittorrent. The `/harbor/portfolio` Infisical credential cannot pull the
homelab NymVPN sidecar image. No pull-secret value is in Git; add a credential
scoped to that repository in Infisical before rotating the secret or rebuilding
Talos. Roll back by stopping Talos NZBGet, restoring the Ubuntu Ingress backend
to its `nzbget` Service, then scaling the Ubuntu Deployment to one. The config
and VPN-state paths are shared, so never run both instances as writers. Keep
the bridge and suspended release until public traffic no longer uses Ubuntu
Traefik.

Vaultwarden's first Talos attempt used its SQLite database on the existing
Synology NFS path. The Pod reached Running/Ready but failed to create the
SQLite pool; `/alive` returned HTTP 502. The source was restored as the only
writer. The retry uses a dedicated PostgreSQL 16.15 Deployment with an
`nfs-k8s` PVC. Its password is synchronized from Infisical at
`/vaultwarden/postgres`. A data-only pgloader rehearsal from the earlier
encrypted archive matched all 28 tables and every row. The final stopped-writer
snapshot decrypted and passed SQLite integrity checks. Its import matched all
28 tables and 860 rows; non-time values matched, and timestamps differed by at
most one microsecond. The Talos Deployment is enabled, with the Ubuntu ingress
Service bridged to Talos ingress `.70`. Eleven direct and bridged samples over
307.8 seconds returned HTTP 200 with the Talos route marker; root and API
configuration responses matched, PostgreSQL and Vaultwarden stayed Ready, and
neither target restarted. The Ubuntu writer remains stopped and its HelmRelease
suspended. Validate a real user login and vault sync before considering the
migration complete. Roll back by stopping Talos before restarting Ubuntu
against the unchanged SQLite directory; never run both instances as writers.
A one-time encrypted custom-format PostgreSQL dump was also created and its
`pg_restore` catalog validated before user validation. It remains outside Git
in the private migration state. The user confirmed login and vault
synchronization on 2026-11-12. A daily CronJob now writes a custom-format
PostgreSQL dump and the full `/data` directory as separate age-encrypted files
to a dedicated 20 GiB `nfs-k8s` PVC, retaining 30 days. A backup was decrypted
on the workstation's tmpfs, its two checksums and all 736 files were verified,
and PostgreSQL restored successfully with 29 tables, one user, and 773 ciphers.
The backup PVC shares the Synology failure domain with live data and does not
replace an independent or off-site copy.

Atuin client synchronization was checked from the workstation on 2026-11-12.
The CLI completed sync against `https://atuin.home.tom-mendy.com` with 14,931
history items and no records pending upload or download. Grafana OIDC login and
live dashboard queries still require a user browser session.

To roll back, suspend the Talos SearXNG Kustomization and stop its Deployment,
then wait until its Pod is gone before starting the Ubuntu Deployment against
the shared NFS path. Restore the Ubuntu Ingress backend to its original
`searxng` Service only after Ubuntu VPN connectivity and health pass. Do not
restore the older pre-cutover archive over state written by Talos; both
clusters use the same NFS directory.

Cinny retained its exact image, configuration, and Matrix homeserver
`matrix.tom-mendy.com`. Public HTML and configuration hashes matched the
Talos copy, and Matrix discovery remained available. The public route uses
the existing Pangolin resource and Newt connector; resource ID 5 and its
existing default authentication policy ID 4 remain unchanged. The source
Cinny Deployment is stopped, while Tuwunel and Matrix RTC remain on Ubuntu.
The Matrix chart now records the separate frontend replica count for thaw.

A preliminary selectorless-Service bridge test exposed persistent upstream
connections that delayed routing rollback. The bridge was removed and the
original Service selector restored. A targets-only Pangolin blueprint then
exposed a compatibility problem: the existing connector/server combination
cleared the HTTP method and briefly returned 503. A full HTTP resource
definition restored the route. Future route changes on this installation must
include the full resource name, mode, domain, TLS setting, and HTTP target
method while preserving existing authentication settings. The valid direct
route was then rolled back to Ubuntu, returned to Talos, and observed for at
least five minutes after stopping Ubuntu Cinny. Both the homepage and config
and the upstream Matrix discovery endpoint passed throughout that window.

Navidrome's user state is SQLite on the approved Synology NFS export. Its
music library is the separate read-only `/volume1/music` export. The target
claims bind the same fixed existing paths with Retain and no node affinity.
The target Deployment must stay at zero replicas until the source writer is
stopped and a final native SQLite snapshot is verified. Generated cover and
transcode caches are recoverable from the pre-cutover file snapshot; user and
playlist state must come from the final stopped-writer database snapshot.
Never run both clusters' Navidrome writers against the shared data directory.

Private evidence and per-service recovery scripts are outside Git:

```text
~/.local/state/homelab/talos-migration/20261111-remaining-services/
```

Application RBAC and manifests are under `talos/bootstrap` and
`talos/gitops/apps`. No credential-bearing Secret is committed. Imported local
TLS Secrets need renewal or replacement by the final target certificate
controller before their recorded expiry; public TLS remains Pangolin-managed.
Do not resume an Ubuntu release or component marked retired during a bulk thaw.

Navidrome completed 305.3 seconds of observation with 30 healthy samples.
Its final stopped-writer SQLite snapshot restored successfully, all 48 table
counts matched, and the running target preserved user, playlist, and share
fingerprints. The full pre-cutover file archive was decrypted and extracted,
with SQLite integrity checked. The target read the existing music export as
the application UID before source shutdown. No database or library path was
replaced by a new empty volume.

The first stopped-writer backup attempt could not create SQLite WAL metadata
through the read-only inspection mount. The source was automatically restored
and remained the only writer. The corrected attempt copied the quiesced
SQLite files into writable temporary recovery space, then took and verified a
native backup there before activating Talos. No manual source database edits
were made. The incomplete initial file-transfer artifact and plaintext restore
checks were removed after the verified encrypted backups were available.

The Infisical administrator action is complete; its identity and Kubernetes
authentication settings are recorded in the
[administrator handoff](talos-infisical-admin-handoff.md). Continue with the
next application individually. Do not boot node3 into an installer yet.

Atuin was migrated to the Talos cluster with its existing application config on
the approved NFS path and a fresh dynamic `nfs-k8s` volume for PostgreSQL. The
Ubuntu HelmRelease remains suspended. After stopping the Ubuntu Atuin writer, a
final custom-format `pg_dump` was encrypted outside Git, decrypted for catalog
verification, and restored with `pg_restore` into the target PostgreSQL 16.15
instance. The source and target both reported six public tables. Atuin uses the
unchanged 18.24.4 image and synchronized database credentials.

The Talos Atuin Pod and PostgreSQL are Ready with no restarts. Direct Talos
ingress and the Ubuntu ingress bridge both return HTTP 200 with the
`talos-atuin` route marker; HTTP redirects to HTTPS. Eleven healthy samples over
306 seconds passed. The Ubuntu Atuin Deployment stays at zero, while its old
PostgreSQL remains available for rollback. Because the target now accepts
writes, rollback to Ubuntu requires either accepting loss of writes since
cutover or first exporting and restoring the target database into the source
PostgreSQL. Do not start both application writers. Keep the ingress bridge and
suspended Ubuntu release until public traffic no longer depends on Ubuntu
Traefik.

Blocky now runs on Talos with the unchanged v0.35.0 image and configuration.
The target has a restricted namespace and uses `10.0.0.71` as its DNS
LoadBalancer. Direct Talos DNS matched Ubuntu for an internal name, a public
name, and a blocklisted name. HTTPS content matched through Talos ingress and
the retained Ubuntu ingress. HTTP redirects to HTTPS, and the metrics endpoint
works through the bridge.

MatrixRTC LiveKit and its JWT service run on Talos at `10.0.0.74` with the
same pinned images as the source. Its LoadBalancer exposes TCP 7880, 7881, and
8081 plus UDP 50100–50110. Ubuntu `matrix-rtc` and `matrix-rtc-jwt` Services
keep their ClusterIPs and route via selectorless EndpointSlices to `.74`; the
Ubuntu Deployment is at zero and the `matrix` HelmRelease remains suspended.
The existing `rtc.tom-mendy.com` ingress and Newt raw routes are unchanged.
Target and bridged `/healthz` and `/` returned HTTP 200 with matching body
hashes in 20 checks over 288.4 seconds; the WebSocket port and JWT health check
also passed, Flux is Ready, and the Talos Pod had no restarts. The user
confirmed a real Element audio/video call works through the cutover.
A dedicated `talos-matrix` Infisical identity now has No Access at organization
scope, Viewer on project `homelab`, and Kubernetes authentication restricted
to the Talos API, namespace `matrix`, and ServiceAccount
`matrix-infisical-sync`; TLS verification uses the Talos CA. Flux now reconciles
the matrix secrets from `/matrix` and `/oidc`, replacing the one-time copied
`matrix-runtime` Secret. Confirm both InfisicalStaticSecrets report Ready before
starting Tuwunel on Talos.

Tuwunel now runs on Talos with the exact `v1.9.4` image and the existing
Synology NFS directories: 50 GiB database and 20 GiB backup paths, bound as
static `nfs-k8s` Retain PVs without node affinity. The Ubuntu Deployment was
stopped before the Talos writer started. Before cutover, a full encrypted
archive of the stopped `/data` and `/backups` trees was created on the
workstation; decryption and streaming tar validation passed (183 files,
90,495,336 bytes). Its SHA-256 and private evidence are recorded outside Git.
The target opened the existing RocksDB schema (version 17), loaded the
existing OIDC signing key, and is Ready. `matrix-runtime` and `matrix-oidc`
are synchronized from Infisical and their secret values matched the source by
SHA-256 without exposing them.

Talos has a dedicated LoadBalancer at `10.0.0.75`. The Ubuntu ClusterIP
Service and existing public Matrix ingress remain as traffic bridges; the
Ubuntu Deployment stays at zero replicas and the Matrix HelmRelease stays
suspended. Public client, federation, server-version, and both well-known
endpoints returned HTTP 200 after cutover with the same body hashes as before
cutover. The client login-flows endpoint advertises SSO. A real user login,
existing room-history check, and message send on the migrated homeserver still
were confirmed by the user in Element after cutover; the migration observation
is complete.

Tuwunel's managed RocksDB backup is now triggered daily by a sidecar sending
the configured `SIGUSR2`; after each signal, Tuwunel creates a managed backup
and verifies its files. Backup #2 passed the built-in verification (all 122
files present at expected sizes). The same job archives `/data/media` and
`/data/archive` to the backup PVC, since the managed database backup excludes
media. Three dated media archives were listed and passed `tar -tzf` integrity
checks; retention keeps seven. These backups share the Synology failure domain
with live data; retain the encrypted workstation archive and arrange an
independent/off-site copy for disaster recovery.

The restarted target was observed for five minutes across 11 public samples:
all six client, federation, server-version, discovery, and login-flows probes
returned HTTP 200 with stable body hashes, and the Pod had no restarts. One
probe batch overlapped the planned single-replica config rollout and returned
HTTP 502; the next sample passed and the uninterrupted observation window
started after the rollout. Flux and both Infisical static secrets are Ready.

The migration is single-writer: never run Ubuntu and Talos Tuwunel together on
the shared NFS database. To roll back, suspend Talos reconciliation, scale
Talos Tuwunel to zero, wait for its Pod to exit, then scale Ubuntu Tuwunel to
one and restore the original Ubuntu Service selector and remove its migration
EndpointSlice. Keep the Ubuntu HelmRelease suspended until the rollback is
verified. Because Talos has already written to the shared database, do not
restore the pre-cutover archive over current data; both clusters use the same
live directory.

To roll back this component, stop the Talos Deployment, restore the Ubuntu
Deployment to one replica, wait for readiness, restore selectors on both
Ubuntu Services, and remove the two migration EndpointSlices. Keep the Matrix
HelmRelease suspended until rollback is verified. Do not move Tuwunel or change
Newt raw routes until the real call passes.

The existing Ubuntu DNS address `10.0.0.61` remains available as a temporary
selectorless Service whose only ready EndpointSlice address is `10.0.0.71`.
The Ubuntu Blocky Deployment is stopped and its HelmRelease remains suspended.
An isolated relay check on `.63` passed before the service cutover. Eleven
checks over 307 seconds passed with the Talos Pod Ready, zero restarts, matching
DNS responses through `.61` and `.71`, public HTTPS returning 200, and HTTP
redirecting to HTTPS. Update DHCP and any statically configured clients to use
`.71` before removing the `.61` relay or retiring Ubuntu. Roll back by starting
the Ubuntu Deployment, waiting for it to become Ready, restoring the Service
selector, and deleting the migration EndpointSlice. Blocky has no persistent
application data.

Grafana was moved to Talos with the exact running image digest and the existing
SQLite database on the same Synology NFS path. Its static PV uses `nfs-k8s`,
Retain, and no node affinity. The final stopped-writer archive decrypted and
passed a full tar readback; SQLite integrity passed with 95 application tables.
The Talos read-only NFS preflight returned the same integrity result and table
count before Grafana started. The Talos config keeps the existing dashboards
and OIDC settings. Its Prometheus datasource uses the HTTPS Prometheus ingress
because the Ubuntu service DNS name is cluster-local; an HTTPS API probe from a
Talos Pod returned HTTP 200.

Public ingress remains on Ubuntu `.60` and forwards through a temporary
selectorless Service to Talos Grafana `.72:3000`. The Ubuntu Deployment is at
zero and its HelmRelease remains suspended. Talos `/api/health` returned 200;
the public response matched it, the login route entered Grafana's generic OIDC
flow, and HTTP redirected to HTTPS. Eleven checks over 308 seconds passed with
no target restarts. An API request using the copied Grafana admin Secret was
rejected, so no admin API check is claimed. The user confirmed browser OIDC
login and current Prometheus dashboard data on 2026-11-12. The copied OIDC
Secret is not Infisical-synced; arrange that source before rotating or
rebuilding the credential.

To roll back, stop Talos Grafana, start the Ubuntu Deployment against the same
NFS database, wait for it to become Ready, restore the Ubuntu Service selector,
and remove the temporary EndpointSlice and Talos `.72` LoadBalancer. Never run
both Grafana writers at once. Remove the Ubuntu ingress and backend bridge only
after DNS and ingress clients use Talos directly.

Pushgateway now runs on Talos with the exact source image digest and no
persistent data. There were no pushed job groups at cutover. The Talos Service
uses `externalTrafficPolicy: Local` so Cilium sees the original Ubuntu Pod
source address and the restricted ingress policy can allow Prometheus. The
Ubuntu Service name and ClusterIP remain stable but are selectorless; its
migration-managed Endpoints object and mirrored EndpointSlice route to
`10.0.0.73:9091`. The Ubuntu Deployment is at zero and its HelmRelease remains
suspended. Eleven checks over five minutes passed with HTTP 200 through the
stable Ubuntu Service, the Prometheus scrape target `up`, the Talos endpoint
ready, and no target restarts. To roll back, scale the Ubuntu Deployment to
one and wait for readiness, restore its original Service selector
(`app.kubernetes.io/instance=prometheus` and
`app.kubernetes.io/name=prometheus-pushgateway`), then verify the Ubuntu Pod
is the sole endpoint and Prometheus is `up`. Keep the HelmRelease suspended
until the rollback is verified. Remove the Ubuntu Service and migration
Endpoints after Prometheus itself has moved to Talos and its scrape is
validated.

Prometheus now runs on Talos with the pinned source chart and image digests.
The source writer was stopped before the target started against the existing
Synology TSDB at `10.0.0.11:/volume1/prometheus`; its Retain PV remains
available for rollback. Talos direct HTTPS and the unchanged public HTTPS
route both returned `/` readiness 200, with the `talos-prometheus` route
marker. The target reports 20 current active targets, all up; a historical
query returned the pre-cutover target count, confirming retained TSDB history.
Grafana `/api/health` remained HTTP 200. The Ubuntu Deployment remains at
zero, its HelmRelease suspended, and the Ubuntu selectorless
Service/EndpointSlice bridge retained.

To roll back, scale Talos Prometheus to zero and wait for its Pod to exit
before restoring the original Ubuntu Service selector and deleting the
migration EndpointSlice; then scale the Ubuntu Deployment to one and verify
readiness. Keep its HelmRelease suspended until rollback is verified. Never
run both TSDB writers at once. Prometheus logs the existing upstream warning
that NFS filesystems may risk data loss; retain the tested recovery backup.

Infisical now runs on Talos with the existing application image v0.166.5 and
Helm chart 1.8.0; this moved the service without combining an application
upgrade. The source app and Redis were stopped before the target started. A
final custom-format PostgreSQL dump was encrypted with Age, decrypted for
verification, and restored into the Talos CloudNativePG PostgreSQL 17.11
cluster. All 795 application tables were present under the `infisical` role.
Talos Redis uses the exact production image digest and the same Synology NFS
data directory as Ubuntu, with AOF enabled. Redis expired 49 TTL keys during
the cutover; no keys were manually deleted.

The Ubuntu ingress still terminates public TLS and forwards through a
selectorless Service/EndpointSlice to Talos ingress `.70`. Direct Talos HTTPS
and the unchanged public HTTPS host returned 200 with matching root response
hashes and the `talos-infisical` route marker. `/api/status` returned 200 and
`redisConfigured: true`. The Talos Infisical operator reauthenticated, and all
seven Talos InfisicalStaticSecrets reported successful reconciliation. Six
checks over five minutes passed with all target Pods Ready and zero restarts.
Prometheus reported 8.87 GiB available on node2 at the final check.

To roll back, stop the Talos app and Redis and wait for both Pods to exit
before starting the Ubuntu Redis writer, since both clusters use the same NFS
directory. Take a fresh encrypted dump of the Talos PostgreSQL database and
restore it into the retained Ubuntu database before restarting the Ubuntu app;
the old database is stale after target writes. Restore the Ubuntu Service
selector from the private snapshot, delete `infisical-talos-ingress`, then
start the Ubuntu app. Keep the Ubuntu HelmRelease suspended until rollback is
verified.

Harbor runs on Talos with the production chart version 1.19.4 and the same
Harbor v2.15.4 component image digests. The Ubuntu Harbor Deployments and
StatefulSets were stopped before Talos mounted the same five Synology NFS
paths. Static PVs use `Retain` and no node affinity; all five target PVCs bound.
The Ubuntu `harbor`, `harbor-config`, and `harbor-extras` HelmReleases remain
suspended, and no Ubuntu Harbor Pod or Service endpoint remains active.

Talos uses its own Infisical Kubernetes identity for namespace `harbor` and
ServiceAccount `harbor-infisical-sync`. The `/harbor` secret and
`/harbor/proxy` credentials synchronize successfully. The Harbor configuration
chart recreated the expected projects and six proxy registries. OIDC remains
`https://authentik.tom-mendy.com/application/o/harbor/`. Harbor's generated
token-signing keypair is supplied through the external Secret
`harbor-token-signing`; this prevents the chart from rotating it during a
reconcile. The encrypted recovery copy is in the private migration evidence
directory and passed Age decrypt-and-compare verification. No secret values are
in Git.

The Ubuntu Traefik HTTPS Ingress now forwards its Harbor host through a
selectorless Service, EndpointSlice, and Endpoints at Talos ingress `.70:80`.
Talos has a separate `web`-only HTTP Ingress for this internal bridge; its
public/direct route remains HTTPS with the copied `harbor-tls` certificate.
Ubuntu continues to terminate public TLS and redirects HTTP to HTTPS. Keep both
bridge resources until public traffic no longer depends on Ubuntu Traefik.

Direct Talos HTTPS and Ubuntu-bridged HTTPS both returned 200 for Harbor's
health API and UI; all eight reported components were healthy. `/v2/` returned
the expected unauthenticated 401, and a bearer-token exchange using the existing
Talos pull credential retrieved the pinned NymVPN image manifest by digest
through the Ubuntu bridge. HTTP on Ubuntu redirected to HTTPS. Six checks over
309.1 seconds passed with all eight target Pods Ready, the Ubuntu namespace at
zero Pods, both HTTPS routes healthy, and no restart counts increasing after
startup.

For rollback, keep the Talos release and all its Pods at zero before starting
Ubuntu, because both clusters use the same NFS directories. Restore the saved
Ubuntu Ingress backend paths while retaining its working ACME TLS resolver,
then restart the source database and Redis and wait for readiness before the
source Deployments. Keep the Ubuntu HelmReleases suspended until rollback is
verified. The original source Ingress and workload objects are in the private
rollback evidence directory.
