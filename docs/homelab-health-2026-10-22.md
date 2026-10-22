# Homelab health check, 2026-10-22

Checks used the live Kubernetes inventory, HTTPS routes, application health
APIs, internal services, Prometheus targets, and Flux resources. Public routes
were tested from the operator workstation, which uses local DNS for most
homelab hosts. These checks do not establish access from every external network.

| Application | Observed result |
| --- | --- |
| Authentik | Login page HTTP 200; SSO takes about 20 to 37 seconds |
| Atuin | HTTPS root HTTP 200; application and database pods ready |
| Autobrr | Public and internal UI HTTP 200 |
| Bazarr | Public and internal UI HTTP 200 |
| Blocky | UI HTTP 200; DNS resolves Authentik to the ingress address |
| Cinny | Chat UI HTTP 200 |
| Coder | UI and health endpoint HTTP 200; workspace pods ready |
| Flux | UI HTTP 200; main Kustomization ready |
| Forgejo | Both hostnames HTTP 200; database and cache health pass |
| Grafana | Health HTTP 200, database OK; login reaches Authentik |
| Harbor | All eight health components healthy; registry returns expected 401 |
| Hindsight | Internal health HTTP 200; public SSO reaches Authentik |
| Homepage | UI HTTP 200; configured metrics endpoint returns HTTP 404 |
| Infisical | UI and status API HTTP 200; PostgreSQL cluster healthy |
| Job search manager | Internal UI HTTP 200; public SSO reaches Authentik |
| Matrix | Client and federation APIs HTTP 200; SSO login advertised |
| Matrix RTC | Local health HTTP 200; public relay returns HTTP 404 |
| Navidrome | Ping HTTP 200; configured metrics route returns HTML |
| NZBGet | HTTP 401 as expected without credentials; both containers ready |
| Ollama | Model listing and four-token generation HTTP 200 |
| OpenWebUI | UI HTTP 200; health reports true |
| Portfolio | Language redirect and final page HTTP 200 |
| Prometheus | Readiness and query UI HTTP 200 |
| Prowlarr | Health API HTTP 200 with no application health issues |
| qBittorrent | Internal UI HTTP 200; public SSO reaches Authentik |
| Radarr | Health API HTTP 200 with no issues; SSO reaches Authentik |
| SearXNG | HTML search HTTP 200; JSON format returns HTTP 403 |
| Sonarr | Health API HTTP 200 with no issues; SSO reaches Authentik |
| Synology DSM | UI HTTP 200 with the certificate's correct hostname |
| Vaultwarden | UI and alive endpoint HTTP 200; metrics HTTP 404 |

All six CloudNativePG clusters were healthy and all PVCs were bound. The
three CronJobs had recent successful executions, including both job search
manager backups. Historical OpenWebUI synchronization failures remain in the
Job inventory, but its latest scheduled execution succeeded.

Harbor's PostgreSQL recovery took longer than the five-minute liveness delay.
Kubernetes requested shutdown before recovery completed, then killed the
process after its termination grace period. The liveness delay now allows
15 minutes and probe commands have a ten-second timeout. Storage remains on
Synology NFS through `nfs-k8s`.

After applying the change and gracefully replacing the database pod, recovery
completed in approximately six minutes and 23 seconds. PostgreSQL became ready
with zero restarts. Harbor's health API reported all eight components healthy,
and `/v2/` returned HTTP 401 as expected without registry credentials.

Prometheus could not verify the Kubernetes API certificate against the migrated
node address, `10.0.0.21`. Its scrape configuration now verifies the certificate
using `kubernetes.default.svc`, which is present in the certificate. The API
target recovered without disabling TLS verification. Three unrelated scrape
failures remain for Homepage, Vaultwarden, and Navidrome. Their old live pod
annotations advertise endpoints that do not provide Prometheus metrics.
Prometheus collects 32 of its 35 configured targets.

The Harbor and Prometheus changes are recorded in the repository values files.
Initially, equivalent inline values were applied on the live HelmReleases.
The next GitOps reconciliation removed those overrides and triggered another
rollout with the old probes. To keep recovery settings active until the
repository changes are published, the live `flux-system` Kustomization now has
two targeted `spec.patches` entries that supply the same HelmRelease values.
GitOps remains active. Once Flux loads the published values ConfigMaps, remove
those two Kustomization patches and the equivalent HelmRelease inline values
so future settings have one source.

The public RTC issue reproduces through the Pangolin address, while a request
using `--resolve rtc.tom-mendy.com:443:10.0.0.60` succeeds. Blocky has no local
RTC mapping, so this hostname also uses Pangolin from the LAN. The existing
Matrix deployment runbook already records this external routing defect.
Repair the Pangolin RTC HTTPS resource and host forwarding before claiming
that calls work outside the cluster. Actual calls were not exercised.

The Homepage DSM link uses `https://10.0.0.11:5001/`, but the NAS certificate
covers `nainjoueur.synology.me` and its subdomains. The service responds, but
that IP-based link fails certificate hostname validation. A request using
`--resolve nainjoueur.synology.me:5001:10.0.0.11` returns HTTP 200 with full
certificate verification.

The check did not submit user credentials, perform downloads, restore backups,
push container images, or test a full video call. Successful login redirects
verify access to Authentik, not a completed authenticated user session.

Ollama generated four tokens with `deepseek-r1:8b` and returned `done: true`.
The request took about 56 seconds, including model loading.

The changed Harbor and Prometheus values rendered successfully with their
deployed Helm chart versions. The storage-policy check and this report's
Markdown check passed. Repository-wide Markdown lint still reports 142
pre-existing issues in 18 other files.
