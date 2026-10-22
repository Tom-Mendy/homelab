# Homelab health check, 2026-10-22

Checks used the live Kubernetes inventory, HTTPS routes, application health
APIs, internal services, Prometheus targets, and Flux resources. Public routes
were tested from the operator workstation, which uses local DNS for most
homelab hosts. These checks do not establish access from every external network.

| Application | Observed result |
| --- | --- |
| Authentik | Login page HTTP 200; SSO takes about 20 to 37 seconds |
| Atuin | HTTPS root HTTP 200; application and database pods ready |
| Autobrr | Initially HTTP 200; intentionally removed during the audit |
| Bazarr | Initially HTTP 200; intentionally removed during the audit |
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
| OpenWebUI | UI and health HTTP 200; SearXNG API returns 20 results |
| Portfolio | Language redirect and final page HTTP 200 |
| Prometheus | Readiness and query UI HTTP 200 |
| Prowlarr | Health API HTTP 200 with no application health issues |
| qBittorrent | Internal UI HTTP 200; public SSO reaches Authentik |
| Radarr | Health API HTTP 200 with no issues; SSO reaches Authentik |
| SearXNG | HTML and JSON searches HTTP 200 after configuration repair |
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

Longer probes alone were insufficient. A later recovery completed, then the
postmaster logged `untracked child process ... exited with exit code 141` and
reinitialized the database. PostgreSQL was PID 1, and the SQL health script
spawns a shell pipeline. This is consistent with a timed-out probe leaving an
orphan that PostgreSQL adopts and mistakes for one of its own failed children.

The Harbor HelmRelease now uses a post-render patch to enable
`shareProcessNamespace` on the database pod. The pod sandbox becomes PID 1
and reaps orphaned processes instead of PostgreSQL. This follows the
[Kubernetes process namespace behavior](https://kubernetes.io/docs/tasks/configure-pod-container/share-process-namespace/).
The database is the only application container in this pod. Its image, data
volume, and storage class are unchanged.

The first pod with the shared process namespace refused to start because the
old `postmaster.pid` still recorded PID 1, now occupied by the sandbox. After
confirming that the previous database pod was gone and PostgreSQL was stopped,
a one-off pod mounted the existing NFS PVC and removed only that stale PID 1
lock. The cleanup pod was deleted after completion. Do not remove a PID file
while a database server can still be using the data directory.

The runtime regression check first failed with `database PID 1: postgres`.
After the patch, `/proc/1/comm` reported `pause`. An orphaned shell subprocess
exiting with code 141 was then reaped without a PostgreSQL reinitialization.
The final recovery completed at 21:01:48 UTC. The orphan regression check was
repeated after the database became ready, and Harbor again reported all eight
components healthy. Four failed container starts from the stale PID file
remain in the pod's restart counter; the counter stayed unchanged after that
lock was removed.

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
The Harbor patch also supplies the process namespace post-renderer. GitOps
remains active. Once Flux loads the published values ConfigMaps and HelmRelease
manifest, remove those two Kustomization patches and the equivalent HelmRelease
inline values so future settings have one source. Keep the post-renderer from
the published manifest.

SearXNG initially returned HTTP 403 for JSON searches both through ingress and
on localhost. OpenWebUI is configured to use this API, so an HTML-only search
test was insufficient. The chart now mounts a settings ConfigMap that inherits
the upstream defaults and enables both HTML and JSON. The secret environment
variable was also corrected from `SEARXNG_SERVER_SECRET_KEY` to `SEARXNG_SECRET`,
as required by the
[SearXNG server settings](https://docs.searxng.org/admin/settings/settings_server.html).
The existing secret reference is retained; no secret value is stored in the
settings ConfigMap.

A third live Kustomization patch applies the equivalent SearXNG deployment
mount and secret environment binding through its HelmRelease post-renderer.
The settings ConfigMap was created with Helm ownership metadata so the chart
can adopt it when the repository changes are published. After publication,
remove this third bridge patch and its corresponding temporary HelmRelease
post-renderer; the deployment template then supplies these settings directly.

SearXNG now uses the `Recreate` deployment strategy because its VPN daemon
stores state on a shared PVC. During the rolling update, the replacement
daemon could not initialize its credential database while the old pod still
used that state. After the old pod stopped and the replacement restarted,
both containers became ready with zero restarts. The service moved from
`node2` to `node3` using the same NFS-backed PVC. No VPN state was deleted.
The temporary post-renderer also supplies this strategy until publication.

The final check ran from the OpenWebUI pod against its configured internal
SearXNG endpoint. A JSON search returned HTTP 200 with 20 results. The public
JSON endpoint also returned HTTP 200, and the SearXNG HelmRelease became ready.

The final cluster inventory contained 96 pods with no unready active pod.
All 41 HelmReleases, the main Kustomization, both image repositories, and both
image policies were ready. Harbor's eight health components remained healthy
after the subsequent GitOps reconciliation.

Concurrent repository changes intentionally removed Autobrr and Bazarr in
commit `fb62856`. Their original HTTP checks are historical; neither application
is part of the final active inventory. The Harbor probe and Prometheus TLS
values were published in `d680a69` while the audit continued. The additional
Harbor process namespace and SearXNG changes remain workspace changes awaiting
publication, together with this report update.

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
deployed Helm chart versions. The SearXNG chart passed Helm lint and rendering,
and the complete Flux configuration rendered with Kustomize. The storage-policy
check and this report's Markdown check passed. Repository-wide Markdown lint
still reports 142 pre-existing issues in 18 other files.
