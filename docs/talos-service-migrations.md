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
| Job Search Manager | Migrated and browser validated | Final PostgreSQL restore (11 tables), exclusive Garage writer on the existing NFS path (29 objects, 4,018,668 bytes), Authentik `homelab-admins` policy preserved; Talos ingress reached through Ubuntu bridge |

Hindsight now runs on Talos with the exact production API and control-plane
image digests. Its pre-bound Retain PV uses the same Synology NFS directory as
the Ubuntu claim; the Ubuntu Deployments were stopped before either Talos Pod
mounted it. The Ubuntu HelmRelease remains suspended, its Deployments stay at
zero, and its HTTPS Ingress bridges to Talos while the more-specific Ubuntu
Authentik outpost route remains in place. Six samples over five minutes showed
both Talos Pods Ready with no restarts; the in-Pod API `/health` and control
plane `/api/health` checks returned 200, and direct plus bridged HTTPS returned
the expected redirect to `authentik.tom-mendy.com`. Browser-side authenticated
validation completed: the dashboard loaded, `/api/version`
and `/api/banks` returned 200, and the existing `hermes` bank with about 1.3k
memories was visible. Ollama is still stopped on Ubuntu and has not been moved,
so Hindsight inference remains unavailable until that dependency is restored.

For rollback, stop both Talos Deployments and wait for all Pods to exit before
starting the Ubuntu Deployments against the same NFS directory. Restore the
Ubuntu Ingress backend from the private snapshot in
`~/.local/state/homelab/talos-migration/20261111-remaining-services/hindsight/rollback/`.
Never run both clusters' Hindsight API writers at once.

Job Search Manager is now running on Talos. The existing Authentik provider
remains in single-application mode on the shared embedded outpost, and its
`homelab-admins` binding stays enabled with policy engine `ANY`. The Talos
forward-auth Middleware uses the provider host outpost endpoint; its in-cluster
probe returned HTTP 200. Browser validation through the public hostname confirmed
authenticated access and the existing application data.

The final PostgreSQL dump was taken after stopping Ubuntu app and Garage writers,
passed gzip verification, and restored all 11 public tables into Talos. Its
SHA-256 is `769c7f1e81ba65c55b9a3a22e9f9582e5b8709cd6c6ef1d3d52422e4ad6e4593`.
Garage uses the same Synology NFS directory on both clusters; simultaneous
instances caused LMDB lock errors and API readiness 503s. Ubuntu app and Garage
were stopped before starting Talos Garage, restoring single-writer access. The
Talos bucket check returned 29 objects totaling 4,018,668 bytes.

Ubuntu Traefik `.60` now forwards the application route to Talos Traefik `.70`
through a selectorless Service and EndpointSlice. The more-specific Authentik
outpost route remains on Ubuntu. Ubuntu Deployments are at zero; Talos app and
Garage are each 1/1 Ready. Ubuntu backup CronJobs are suspended; Talos PostgreSQL
and object backups are enabled and both manual backup runs succeeded. The Talos
backup PVC contains a fresh PostgreSQL dump and 29 object files. Keep Ubuntu
HelmRelease suspended and its writers at zero until rollback is required. For
rollback, stop Talos app and Garage and wait for their Pods to exit before
starting Ubuntu writers; restore the saved Ubuntu Ingress backend from the
private pre-cutover snapshot. Reverse any post-cutover database writes before
rolling back.

Six samples spaced one minute apart over 301 seconds confirmed stable health,
public Authentik redirection, and exclusive Garage access. The app and Garage
remained Ready 1/1 with zero restarts, Ubuntu writers stayed at zero, and no new
LMDB contention appeared.
