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
| Grafana | Migrated, observed, and browser OIDC/dashboard validation confirmed | SQLite on Talos; Prometheus source remains Ubuntu; Ubuntu ingress bridge retained |
| Vaultwarden | Migrated and user validated | PostgreSQL on Talos; Ubuntu SQLite writer stopped; Ubuntu ingress bridges to Talos .70 |
| MatrixRTC | LiveKit/JWT component migrated and observed; real call pending | Talos `.74`; Ubuntu Services and public ingress bridge to Talos; Tuwunel and Newt remain Ubuntu |

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
also passed, Flux is Ready, and the Talos Pod had no restarts. A real Element
audio/video call has not yet been tested and must pass before migrating
Tuwunel. The target `matrix-runtime` Secret was copied from the Ubuntu source
without logging values; it is not yet synced from Infisical, so establish the
Talos secret source before credential rotation or rebuild.

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
