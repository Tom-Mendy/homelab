# Talos migration tracker

The production etcd CA rotation completed on 2026-11-26. The three
phases staged overlapping trust, switched certificates, and removed the
previous CA. Each phase rebooted one node at a time. All three voting
members and direct Kubernetes API readiness checks passed after each
reboot. The final applied Raft indexes matched. Each node trusted only
the replacement CA, and its peer certificate verified against that CA.
The pre- and post-rotation snapshots passed checksum verification.
The three-member etcd 3.7.3 rehearsal preserved data and writes through
the rotation and rejected the old client afterward. A rehearsal without
restarts failed at the first issuer switch.
Harbor and the CloudNativePG operator recovered after container image
pulls delayed their startup.
Several pending workloads were rescheduled to nodes with cached images.
All six CloudNativePG databases returned to healthy. Harbor, Authentik,
Forgejo, and Infisical returned HTTP 200 on their health endpoints, and
the Sumfeet runner accepted a GitHub Actions job after recovery.
Open WebUI recovered on node3 after its old pod on node1 terminated.
Open WebUI and Ollama both returned HTTP 200. The Hindsight and
Harbor configuration Flux charts and releases returned to Ready after
reconciliation against the existing Git artifact.

Blocky now allows `mcp.posthog.com` and `oauth.posthog.com` in its
strict list group. Flux rolled out the change with the existing
Blocky image. Both DNS addresses returned public IPv4 and IPv6 answers for
the two names and preserved the Forgejo LAN mapping. The PostHog
OAuth metadata endpoint returned HTTP 200 through normal DNS.
Codex reached the OAuth consent step. User authorization is pending.

On 2026-11-27 Authentik returned HTTP 503 and reported two corrupt
PostgreSQL indexes. Both were rebuilt concurrently and the replacement
server pod passed readiness. Infisical Redis failed to load its AOF.
The repair removed a 65,281-byte zero-filled gap and retained the four
complete commands after it. The repaired copy passed Redis validation
and started in an isolated container. The original archive was saved
outside the cluster, and the original incremental file was retained on
Synology. Redis and Infisical returned to Ready. A subsequent baseline
probe passed for both DNS addresses, all six PostgreSQL clusters,
and the application health endpoints. The source of the corruption was
not established.

The Sumfeet ARC scale set `arc-runner-set-sumfleet-tom` now runs on Talos.
ARC 0.15.1 uses the existing repository configuration, a project pull-only
Harbor credential, and a dedicated runner namespace for Docker-in-Docker.
GitHub reported the Talos runner online and idle, and the runner reported
that it was listening for jobs. The runner also reached its Docker daemon.
The Talos override keeps one runner online and caps concurrency at one.
Flux now manages the existing ARC controller and Sumfeet scale set
from the digest-pinned charts in the `arc-sumfeet` Kustomization.
The pinned chart renders matched both installed releases before adoption.
Both HelmReleases and the Kustomization reported Ready after adoption.
The GitHub and Harbor credentials remain Kubernetes Secret references.
Automated credential synchronization remains pending. The existing
GitHub runner identity returned HTTP 401 during Kubernetes TokenReview
with a token from its Talos service account. The temporary service account
used for the probe was removed. The running ARC releases still use the
verified Kubernetes Secrets. Update the identity through an Infisical
administrator session and validate a separate sync target before
switching the existing Secret.

The Talos API authority was rotated on all three nodes. The previous
client configuration was rejected by every node, and the replacement at
`~/kube/talosconfig` authenticated to each one. All nodes stayed Ready
and etcd reported matching applied Raft indexes. A pre-rotation etcd
snapshot and the new machine configurations were verified and stored
privately. Kubernetes API trust, etcd trust and the service-account
signing key are separate. The Kubernetes API rotation has now
completed. An initial run stopped during trust staging after a private
key fragment appeared in an inspected log. Its temporary trust was
removed, and a different CA was staged and applied one node at a time.
All three APIs rejected the previous administrator credential, and the
replacement kubeconfig is installed at `~/kube/talos-homelab.yaml`.
All four Infisical identities authenticate with the final CA as their
sole trust anchor. The post-rotation etcd snapshot passed checksum
readback, and all three machine configuration exports passed validation.
All 58 projected service-account tokens used by running pods were
verified before removing the previous public key. Talos applied the
change on one control plane at a time without host reboots. Each API
passed readiness, advertised only the replacement key, rejected the
old Infisical reviewer token, and accepted its replacement. A second
audit confirmed all 58 projected tokens used the replacement key. The
post-change etcd snapshot passed checksum verification.
The exposed Kubernetes bootstrap token was replaced in all machine
configurations and revoked in the API. TokenReview accepted the
replacement and rejected the old token. The Talos machine bootstrap
token was also replaced and checked in the live trust service on all
three nodes. Etcd uses its CA for both peer and client trust. Service-account signing
changes require new Infisical reviewer JWTs and checks for workloads
using mounted service-account tokens.

Harbor switched to the visible Infisical identity `talos-harbor-sync`.
It has no organization role privileges and Viewer access in the homelab
project. Kubernetes authentication is restricted to the existing Harbor
sync service account, with API TLS verification enabled. A fresh login
using a token for that service account succeeded before the switch.
The former identity remains available for rollback. Flux now reconciles
Harbor and Blocky from commit `132d80b3d59eb8c4107c7a24d78dcf49b719e3c4`,
which contains the new identity and tested DNS configuration.

Navidrome was stopped on node2 and then started on node3 with the same
Synology data and music volumes. The ingress briefly returned HTTP 502
before the application returned HTTP 200. Node2 was uncordoned and the
Navidrome Flux Kustomization resumed and reported Ready.

The API VIP returned Ready on all 15 probes during a controlled node1
reboot. The node returned Ready with a new boot ID. Each control-plane API
also passed direct TLS readiness checks, and the etcd members reported the
same applied Raft index. A test file on the existing validation NFS claim
survived moves from node2 to node3, node1, and back to node2. In a separate
test, node2 relinquished the API VIP without rebooting. Node3 took over
and the VIP passed readiness probes. Node2's configuration was restored.
The outage preflight found all
six CloudNativePG primaries on node2, with zero allowed disruptions.
Fresh logical backups for the six clusters passed gzip and SHA-256
verification. All six dumps also restored into separate local PostgreSQL
instances using their source major versions. The restore stopped on
SQL errors and matched each COPY row count against the dump. The local
bootstrap postgres role already existed, so the restore stream skipped
only its duplicate CREATE ROLE statement. The saved dumps are unchanged.
All six original PVCs are bound to Synology NFS volumes with no node
affinity.

For each relocation, cordon node2 and gracefully delete only the current
primary pod. Wait for CloudNativePG to recreate it elsewhere. Verify
that it uses the original PVC UID, accepts queries as primary, and
passes its application check before proceeding. Leave the PDBs enabled
and preserve all PVCs. An orderly stop can include CloudNativePG's
three-minute smart shutdown timeout. Confirm a way to restore power
before a full shutdown.

All six primaries were relocated to node3 one at a time. Each accepted
a PostgreSQL query as primary and passed its application check. The
original six PVC UIDs and all six PDBs were preserved. The first move
also waited for the PostgreSQL image to download. The pinned database
images were warmed on the surviving nodes before the later moves.
The remaining managed workloads were evicted individually and checked
for Ready replicas on node1 or node3. Only static control-plane pods,
DaemonSets, and four standalone test pods remained on node2. Node2
was uncordoned after relocation. At the final
sample, kubelet reported 4.43 GiB available on node1 and 21.16 GiB on
node3. The API VIP, both Blocky addresses, and the application checks
passed. A new etcd snapshot passed SHA-256 verification. Physical access was
confirmed before shutting down node2.
The private outage probe script passed a baseline run for both surviving
APIs, the API VIP, both Blocky addresses, six PostgreSQL clusters, and
application health. All 61 probe rounds passed during the 30-minute node2 shutdown.
The API VIP, both surviving API endpoints, both DNS addresses, all six
PostgreSQL clusters, and the sampled applications passed every round.
Minimum available memory was 4.37 GiB on node1 and 17.55 GiB on node3.
After power-on, node2 returned Ready and its direct Kubernetes API
passed readiness. All three etcd voters reported the same applied Raft
index and leader. Node2 was uncordoned and the health probes passed again.

Cloudflare's DNS-only wildcard for `*.home.tom-mendy.com` now points to
`10.0.0.70`. The distinct Talos API record still points to `10.0.0.65`.
Job Search Manager recovered after the DNS change, installation of a
project-scoped Harbor pull credential, and repair of the registry's
internal password hash. The Deployment pulled its existing pinned image.
The corrected registry hash was saved in Infisical and synchronized back
to Kubernetes. Both the mounted and synchronized hashes matched the
registry password. The project pull credential retrieved the pinned
manifest from Harbor and its SHA-256 matched.

Talos cert-manager v1.21.3 issued all 27 production ingress certificates
through Let's Encrypt and Cloudflare DNS-01. Traefik served the newly issued
certificates on the LAN VIP. The Coder certificate renews on 2027-01-24.
The issuer uses a Kubernetes Secret for the Cloudflare API token and a
separate ACME account key. The private values stay outside Git. The
[issuer and certificate manifests](../talos/bootstrap/pending/cert-manager/)
record the pinned installation configuration and renewal targets.

The old DNS IP `10.0.0.61` now belongs to a Talos MetalLB pool that contains
only that address. Ubuntu released the IP and excluded it from its pool
before Talos announced it. Both `.61` and `.71` answered DNS and served
Blocky metrics. The workstation's DHCP-provided resolver at `10.0.0.1`
also resolved migrated names to Talos.

Newt replaced the public Coder and qBittorrent backend targets with
`10.0.0.70:443`. Their public health and outpost probes passed. Public
Forgejo Git over SSH returned the expected repository HEAD through
Pangolin, and the Newt pod reached the Talos Forgejo Service on port 22.

Three probe rounds passed while Ubuntu's Traefik VIP `10.0.0.60` was
withdrawn. They covered public Authentik, Coder, Forgejo HTTPS and SSH,
Matrix, Cinny, qBittorrent, Radarr, Sonarr, and DNS on both Talos VIPs.
The Ubuntu ingress VIP was restored as a rollback path.

Fresh Ubuntu and Talos etcd snapshots and a Git bundle passed checksum
readback. Node1 booted the verified non-GPU Talos v1.14.5 ISO. Its wired
MAC and SanDisk SSD WWID matched the observed hardware. The final
configuration excluded Flannel and selected only that SSD. Node1 booted
from the SSD and joined the existing cluster as its third control plane.
All three nodes became Ready, all three etcd members are voting, and the
API VIP passed its readiness check. A post-join etcd snapshot passed
checksum readback. Controlled node failure tests remain pending. Preserve
the Ubuntu HDD for rollback. CI runners remain paused.

Both Forgejo LAN names now resolve to Talos ingress at `10.0.0.70`
through both DNS resolvers. Traefik serves the imported TLS certificates
and forwards TCP port 22 to Forgejo. The ED25519 host key matched the
existing key, and an authenticated `git ls-remote` returned the same
repository HEAD before and after the switch. During the Traefik rollout
the ingress VIP changed nodes and a probe briefly failed. HTTPS and SSH
passed after the announcement moved. The public Ubuntu bridge remains
available. The Talos Flux Git source still uses the dedicated SSH VIP
`10.0.0.76`.

The Flux web UI now resolves to Talos through both LAN resolvers. The UI
uses the existing Authentik OIDC client and TLS certificate. Unauthenticated
API requests returned HTTP 401, and the authorization route reached the
Authentik sign-in page. The two existing groups have read-only access to
selected Flux and workload resources on Talos. Impersonation checks
confirmed that both groups can read ResourceSets and that Kubernetes
denies Secret reads and Kustomization patches. A signed-in session remains
to be verified. The Ubuntu route is available for rollback.

Matrix, Cinny, Harbor, qBittorrent, and Job Search Manager now resolve
to the Talos ingress VIP through both LAN resolvers. The Matrix route uses
the existing ACME certificate and passed client discovery, federation
version, and well-known checks. Cinny configuration and Matrix client
versions also returned HTTP 200 through public DNS. A Matrix call has not
been tested. Harbor returned the expected registry authentication challenge.
Both protected applications redirected to Authentik, and their HTTPS
outpost pings returned HTTP 204.

Authentik, Coder, Ollama, and Open WebUI now have direct HTTPS routes on
Talos. Both DNS resolvers serve the Talos VIP for these four names.
Existing ACME certificates were transferred as Kubernetes TLS Secrets.
Cert-manager has since replaced the imported certificates.
Authentik discovery advertised the HTTPS issuer. Open WebUI restarted
on node3 and its login redirected to Authentik over HTTPS after switching
the internal host alias to Talos. A signed-in session was not tested.

Blocky now answers with the Talos ingress VIP `10.0.0.70` for 13 names
whose direct HTTPS routes were checked. The new answers were verified
through Talos DNS `10.0.0.71` and the Ubuntu relay `10.0.0.61`.
The pinned Git source now includes the Blocky mappings and rolling
deployment strategy. Talos has also taken over the Ubuntu DNS relay address.

Newt moved from Ubuntu node1 to Talos node3 using the same tunnel identity.
The Ubuntu Deployment is stopped. The restored Matrix RTC service name
resolves on Talos and Newt marked the TCP target healthy. A Matrix call
has not been tested. Radarr and Sonarr now route from Newt directly to
Talos HTTPS. The initial attempt timed out because the Talos HTTPS
entrypoint lacked the outpost routes. After adding the secure outpost
routes, both applications returned HTTP 302 and both outpost pings
returned HTTP 204. Cinny still returns HTTP 503 through the public
tunnel, as it did before the Newt move. Its direct Talos ingress passed.

Node3 booted Talos v1.14.5 from the Crucial NVMe on 2026-11-24. The
maintenance API confirmed the wired MAC and the sole internal disk serial.
The reviewed configuration selected that serial and removed the old
Flannel document to match the Cilium cluster. An etcd snapshot with a
SHA-256 checksum was saved privately before applying the configuration.
Node3 joined the existing cluster without bootstrap. Both voting etcd
members were healthy with matching applied indexes. Both nodes and both
Cilium DaemonSets were Ready. A scratch NFS claim passed a write and read
in both directions between node2 and node3. The four public health
endpoints checked after the join all returned HTTP 200.

Node3 loaded NVIDIA driver 580.178.04 and detected a GPU. Kubernetes
advertises one allocatable GTX 1080 after the NVIDIA device plugin
registered with kubelet. The Talos `nvidia` RuntimeClass and plugin
are restricted to node3. An isolated pod using the pinned Ollama 0.40.13
image generated a response with SmolLM2 and reported 100% GPU on driver
580.178.04 and toolkit 1.19.1. Ollama was then enabled on Talos with its
existing Synology claim. The Ubuntu ingress forwards to Talos and the
Open WebUI pod reached the service and found all three existing models.
The old Ubuntu Deployment remains stopped.
Cold-load requests for Gemma4 and Spark exceeded client timeouts of
160 and 245 seconds respectively while reading weights from NFS.
The API remained available. Inference for these two production models
was not verified; the isolated GPU result only covers SmolLM2.
Both voters are required for quorum until a third control plane joins.

On 2026-11-24, the Ubuntu Flux and Actions Runner Controller workloads
and both runner listeners moved to node1. Runner limits remained at zero.
The FluxInstance now references Forgejo on Talos. Its reconciliation is
still frozen, so the Deployment placement was applied live. All three
Ubuntu Git sources and the Talos source reported Ready.

Node3 was cordoned, drained, and shut down gracefully over SSH. The drain
evicted only two completed jobs and left the node-scoped system pods.
After SSH stopped responding, Authentik, Coder, Open WebUI, and Forgejo
health endpoints returned HTTP 200. Blocky DNS and the Talos Git source
also remained available. The Crucial file archive checksum was reverified.
The physical handoff is to disconnect power, retain only the Crucial
CT500P1SSD8 serial `1950E22ED071`, keep all removed disks intact, and boot
the prepared NVIDIA USB into maintenance mode. Confirm disk serial and
wired NIC MAC `18:c0:4d:a5:82:00` from maintenance mode before installing.

Forgejo production moved to Talos. The read-only precopy contained 3,930
files and the final stopped-writer rsync transferred no changed files.
The final database dump restored on Talos. The SSH host key matched the
original key. Flux on both clusters fetched the repository through Talos
`10.0.0.76:22`. Ubuntu retains the public TLS and SSH front ends, which
now forward to Talos. Both public HTTPS health routes and the SSH host key
through the Ubuntu VIP passed. The Ubuntu Deployment remains stopped and the
old database was marked for hibernation. The Talos source manifest uses the
direct endpoint. The legacy Ubuntu .62 service is kept for rollback.

The obsolete Ubuntu CloudNativePG clusters for Coder, Infisical, Job Search
Manager, and Open WebUI report hibernation complete. Their Talos replacements
are Ready and the Ubuntu claims were retained. Authentik's obsolete primary
is still shutting down. Its remaining idle sessions belonged to retired
Ubuntu pod addresses. The old Atuin PostgreSQL Deployment was scaled to zero
after confirming no clients. Its public ingress already forwards to Talos.

Forgejo's target PostgreSQL on Talos restored 128 tables on a new NFS claim.
The stopped target Deployment has a claim prebound to the existing Synology
`/volume1/forgejo` export. Talos assigned `10.0.0.76` for SSH. The
target ingress and Ubuntu HTTP/SSH bridge are staged. Forgejo still runs on
Ubuntu node1. At cutover, stop the Ubuntu writer, archive the file volume,
restore the final database, and verify the same SSH host key and repository
read before repointing Flux and the public routes.

The first Forgejo cutover stopped the Ubuntu writer, but the archive went
slowly through loose Git objects on the NAS. The copy was interrupted to
restore service. Forgejo health passed after restart and Talos Flux fetched
the same revision again from Ubuntu .62. The incomplete archive is marked
`.partial` and cannot be used as the cutover backup. A read-only rsync
precopy runs with Forgejo online. After it completes, briefly stop Forgejo
for the final delta, capture the final database dump, and then verify the
target SSH key before enabling the suspended Talos source probe.

The old Authentik database also completed hibernation. The Ubuntu
CloudNativePG controller moved to node1 and the Ubuntu Forgejo database
remained healthy.

Open WebUI moved to Talos using its existing Synology data directory and a
new PostgreSQL NFS claim. With the Ubuntu StatefulSet stopped, the volume
archive passed full readback and the final database dump restored 48 public
tables. The public Ubuntu ingress forwards to Talos through
`openwebui-talos-bridge`. Health and the HTTPS OIDC redirect and callback
were verified. A signed-in session and inference remain unverified.

Open WebUI temporarily used the Ubuntu TLS VIP for
`authentik.tom-mendy.com` because the public tunnel returned HTTP 503
from its pod. The alias now points to the Talos HTTPS VIP `10.0.0.70`.
Ollama remains scaled to zero on Ubuntu, and function synchronization
remains suspended. The old Open WebUI PostgreSQL instance remains on node3.

Temporary live placement overrides moved the Ubuntu MetalLB controller, NFS
provisioner, Traefik, Forgejo application, and Newt to node1. Node3 was
excluded from MetalLB after Forgejo's local SSH endpoint moved to node1.
All three Ubuntu VIPs (.60, .61, .62) announced from node1. Authentik HTTPS
readiness, Blocky DNS, the Forgejo SSH host key, and Talos Flux source
reconciliation passed. Newt logged that client connectivity was ready.
The controls did not require changing node1's control plane taint.

Forgejo PostgreSQL switched to node1 after the replica replayed the WAL
checkpoint and matched the cluster identifier and 128 public tables.
Forgejo's database health check passed on the new primary. CloudNativePG
returned to one healthy instance. The old NFS volume used Retain.
All six Ubuntu PostgreSQL dumps passed full pg_restore readback and
SHA-256 verification in the private node3 release directory.

The Ubuntu Coder Deployment moved to node1 and its service returned OK
on /healthz. The Coder primary remains on node3 while CloudNativePG
creates a replica on node1. The database system identifier, WAL
checkpoint, and table count are recorded in the private release directory.

Coder moved directly to Talos. Its PostgreSQL cluster was provisioned using
[`coder-postgres.yaml`](../talos/bootstrap/pending/coder-postgres.yaml).
It uses the same PostgreSQL image and a new Synology NFS claim. After the
Ubuntu writer stopped, a final dump was restored in one transaction.
The target returned 119 public tables and four workspace records. Coder
chart 2.38.5 runs on Talos through a staged Helm release and
[`coder-ingress.yaml`](../talos/bootstrap/pending/coder-ingress.yaml).
Ubuntu still terminates public TLS and forwards Coder traffic to Talos
through the `coder-talos-bridge` service. Public health and login endpoints
responded and the OIDC callback redirected to `authentik.tom-mendy.com`.
The Ubuntu Coder Deployment remains at zero and its HelmRelease suspended.

Three workspace claims are prebound on Talos to their original Synology
paths with Retain. Both clusters block workspace pods with a quota.
Complete an authenticated Coder login and verify a controlled workspace
start before opening workspace scheduling. Preserve the final dump and the
old database. If rolling back after Talos has accepted writes, quiesce Coder
and transfer the current database before bringing the Ubuntu writer back.

The temporary Authentik move to Ubuntu node1 rolled back. Kubernetes
reported the new server Ready, but the first HTTPS probe through the VIP
timed out at five seconds. After rollback, the application Service, node1
Traefik NodePort, and the Ubuntu VIP responded. Three VIP probes returned
HTTP 200 in 3.06 to 3.26 seconds. The cause of the earlier timeout remains
unconfirmed. For the direct Talos cutover, verify the application Service
and target ingress independently, then observe the public route and OIDC.

The Authentik rehearsal on Talos restored 230 public tables to a new
Synology NFS claim. The task-log integrity check passed and all seven
archived rows were present. The isolated server became Ready and its
Service health check passed. The rehearsal server was then scaled to zero.
The worker stayed stopped during rehearsal.

Authentik production moved to Talos after both Ubuntu writers stopped and
the final dump restored. The first attempt rolled back when Traefik had not
yet loaded the target route. The second attempt staged the route before the
outage and waited for backend discovery. Ubuntu still terminates TLS and
forwards the main route and all five outpost paths to Talos .70. The three
Ubuntu ForwardAuth middlewares use the existing public outpost paths.
The Talos ingress middleware restores the HTTPS scheme at the backend
because the bridge uses HTTP. OIDC discovery now advertises the HTTPS issuer.
The Talos server, worker, and database are Ready. Public health and Coder
health returned HTTP 200, all five outpost pings returned HTTP 204, and
protected endpoints returned HTTP 302. A signed-in session remains to be
verified. The old database remains available for recovery.

Ubuntu kube-state-metrics rolled from node3 to node1. The Deployment has a
temporary live hostname selector and control plane toleration for node3
release. The Service reported a ready endpoint on node1. If reconciliation
reverts the patch, recheck placement before releasing node3.

On 2026-11-23, the operator selected the Crucial CT500P1SSD8, serial
`1950E22ED071`, as the sole node3 Talos disk. Keep the other four disks
intact. Confirm the Crucial serial again from the NVIDIA ISO in maintenance
mode before installing.

A live file archive of the Crucial root, home, boot, and EFI filesystems
completed on 2026-11-23. The private copy is
`~/.local/state/homelab/node3-release/node3-crucial-20261123T194945.tar.gz`.
The full archive listing passed and includes the home directory, EFI directory,
and fstab. The adjacent checksum records the archive SHA-256. This is a file
backup. A bootable restore has not been attempted.

The Ubuntu kubelet reported 3.93 GiB available on node1 and 5.46 GiB of pod
working set on node3. Talos node2 reported 7.69 GiB available. These are
point-in-time measurements. Do not move all Ubuntu pods onto node1 together.
Atuin, Infisical, and Job Search Manager have active applications on Talos
with database pods remaining on Ubuntu. Verify consumers and recovery copies
before stopping those Ubuntu databases. Keep Forgejo at `10.0.0.62:22`
reachable because the Talos Flux source still uses it. Preserve Ubuntu
Traefik and Newt until their remaining routes have been verified elsewhere.

On 2026-11-18, the Ubuntu API was reachable using `~/.kube/config`.
Node3 still had 39 pod records, including Forgejo, Newt, Traefik, and
Open WebUI. Six PostgreSQL primary disruption budgets allowed zero evictions.
Node1 still had its control plane NoSchedule taint. No Ubuntu PV reported a
local source, hostPath source, or node affinity. Host mounts and disk contents
were inspected by SSH on 2026-11-19. Ubuntu boots from the Crucial CT500P1SSD8
(`1950E22ED071`), which also holds root and home. The Samsung 980 PRO 1 TB
(`S5GXNF0TB14116F`) holds `/var/lib`, including kubelet state. Three other
disks hold `/usr` (Samsung 840), `/var` (SanDisk), and `/srv` (Toshiba).
Preserve all disks for Ubuntu rollback and inspect or back up needed host
data before removing or overwriting any of them.

Before releasing node3, verify which Ubuntu endpoints and database writers are
still used, check destination capacity, and relocate active workloads with
application checks. Handle each singleton database separately. Keep the
Ubuntu boot disk available for rollback and confirm the intended NVMe serial
in Talos maintenance mode before applying the installation configuration.

Last updated: 2026-11-12. This file is the migration progress record.
Steps 1 and 2 are complete. Talos v1.14.5 is installed and bootstrapped on
node2 (Kubernetes v1.36.6, node Ready). Step 3 foundation validation is
complete, including Cilium NetworkPolicy enforcement, DNS, isolated NFS,
MetalLB, HTTPS ingress, and recovery after reboot. Step 4, selective GitOps,
has a validated restricted bootstrap. Production applications are migrating
individually; see step 5.

Build a separate Talos cluster on node2, migrate applications individually,
then convert node3 and finally node1. The target is three control-plane nodes
that also accept application workloads. An additional temporary machine is
preferable if capacity or service dependencies prevent this sequence.

Keep application versions unchanged during migration. Record each operation,
validation result, rollback decision, and remaining dependency here. A checked
box means the work was verified, not merely planned.

1. Prepare without disrupting production. Status: complete.
   - [x] Inspect live nodes, workloads, storage, placement, PDBs, databases,
     scheduled jobs, and GitOps state.
   - [x] Export current PVC/PV/NFS bindings and workload image versions
     outside Git.
   - [x] Create and verify an external-to-cluster Git bundle.
   - [x] Run the repository storage policy check.
   - [x] Validate capacity and placement for operation without node2, including
     peak demand and workloads with missing resource requests.
   - [x] Complete current application-native backups and isolated restore tests.
   - [x] Securely preserve bootstrap credentials, encryption keys, administrator
     recovery access, and Talos configurations outside the cluster.
   - [x] Prepare isolated Ubuntu and Talos access files without changing the
     existing default context. Talos Kubernetes credentials fail closed until
     real bootstrap authentication can be retrieved and validated in step 3.
   - [x] Prepare the version baseline and suspend/protect image update automation.
     Pin the final reviewed Git revision and satisfy publisher/digest gates at
     the maintenance window; an inventory export alone does not freeze versions.
   - [x] Revalidate Talos configuration and supported versions; prepare a
     Talos-only API endpoint and separate load-balancer allocation.
   - [x] Prepare the mandatory ISO disk/NIC inspection procedure. Actual disk
     selection remains a hard stop immediately before installation in step 3.
   - Gate: tested recoverability and sufficient remaining Ubuntu capacity.
     Do not drain or reinstall node2 until this gate passes.
2. Release node2. Status: complete.
   - Move workloads in a maintenance window, handling singleton databases and
     their PDBs explicitly. Do not bypass every PDB by default.
   - Verify application access and observe Ubuntu without node2 before erasing it.
   - Rollback before reinstall: restore scheduling on node2 and verify services.
3. Install Talos on node2. Status: foundation complete.
   - [x] Confirm the physical installation disk from the ISO before applying
     config. Inspection on 2026-11-08: NIC `enp0s31f6`, MAC
     `10:7b:44:18:50:de`, disk Kingston SNVS250G serial
     `50026B73811E4F0E`. Evidence in the private
     `20261108T1052-node2-final/iso-inspection.json`.
   - [x] Install Talos v1.14.5 with `wipe: true` (approved) via
     UnattendedInstallConfig; the initial `disk.dev_path` selector matched no
     disk and was corrected in the node config to
     `disk.serial == "50026B73811E4F0E" && disk.transport == "nvme"`.
   - [x] Bootstrap the new cluster once; node2 is Ready on Kubernetes v1.36.6
     with etcd member `node2`, flannel/kube-proxy/CoreDNS running, and the
     10.0.0.65 API VIP announced. The real kubeconfig was retrieved into a
     private file with context `talos-homelab`, endpoint
     `https://talos-api.home.tom-mendy.com:6443`, and validated (TLS SAN,
     `/readyz`). Ubuntu access files and the default context are unchanged.
   - [x] Validate Cilium 1.20.4, DNS, NetworkPolicy deny/allow, isolated
     nfs-k8s persistence, MetalLB, and HTTPS ingress with disposable test data.
     Flannel was replaced; kube-proxy remains. Application operators will be
     introduced individually with selective GitOps. See the
     [foundation validation record](talos-foundation-validation.md).
   - [x] Use an API endpoint that reaches Talos only. Allocate non-overlapping
     MetalLB pools and ingress addresses across both clusters.
   - [x] Reboot node2 and verify network, NFS permissions, and persistence
     before migrating production data. A one-member control plane has no
     failover.
4. Prepare selective GitOps. Status: restricted bootstrap complete.
   - [x] Install pinned Flux without image automation and validate a dedicated
     read-only Forgejo source, commit pin, artifact filter, and restricted RBAC.
   - [x] Reconcile the isolated validation-only root from the migration branch.
     See [selective GitOps](talos-selective-gitops.md).
   - [x] Prepare application-specific credentials and operators, establish
     target ingress, and complete production traffic cutovers individually.
   - Use an explicit Talos application allowlist. Do not reconcile the complete
     production application tree into the new cluster.
   - Prepare an external Git bootstrap source or temporary reachable Ubuntu
     Forgejo endpoint. Prepare Infisical credentials for the new Kubernetes identity.
   - Replace temporary cross-cluster service dependencies with reachable
     endpoints. Cluster-local service names do not span clusters.
5. Migrate applications individually. Status: Portfolio, Cinny, Navidrome,
   SearXNG, Homepage, Radarr, Sonarr, Prowlarr, qBittorrent, NZBGet, Atuin,
   Blocky, Pushgateway, MatrixRTC, Tuwunel, Hindsight, and Job Search Manager
   migrated and validated.
   - [x] Move Cinny with its unchanged image and homeserver, verify routing
     rollback, and observe public HTML/config plus Matrix discovery.
   - [x] Move Navidrome after native SQLite/file recovery checks, preserve
     users/playlists/shares, and pass a five-minute observation.
   - [x] Create the separate Talos Infisical identity, synchronize both
     SearXNG Secrets, preserve the stopped-writer NymVPN state, and verify
     connected Swiss egress and five-minute routing stability. See the
     [admin handoff](talos-infisical-admin-handoff.md) and
     [service execution record](talos-service-migrations.md).
   - [x] Move Prowlarr with the stopped-writer SQLite snapshot, verify both
     Radarr/Sonarr application connections, preserve its login route, and pass
     a five-minute observation. Talos-wide HTTP-to-HTTPS redirection must be
     validated before external traffic bypasses Ubuntu Traefik.
   - [x] Move Atuin after a stopped-writer PostgreSQL dump and logical restore,
     preserve its existing config path, bridge HTTPS through Ubuntu, and pass
     a five-minute observation. Rollback after target writes requires a reverse
     database restore. See the [service execution record](talos-service-migrations.md).
   - [x] Move Blocky with its unchanged config and image; retain the stable
     Ubuntu DNS IP as a tested UDP bridge to Talos, validate HTTPS and DNS, and
     pass a five-minute observation. Update DHCP/static DNS clients to `.71`
     before removing that bridge. See the
     [service execution record](talos-service-migrations.md).
   - [x] Move Grafana with its stopped-writer SQLite snapshot and same NFS
     database path; keep Prometheus reachable over HTTPS, bridge public ingress,
     and pass a five-minute observation.
   - [x] Move Pushgateway without persistent data; preserve its Ubuntu Service
     address through a selectorless bridge to Talos and pass a five-minute
     Prometheus scrape observation.
   - [x] Verify Atuin client synchronization from the workstation CLI on
     2026-11-12; sync completed with 14,931 history items and no records
     pending upload or download.
   - [x] User confirmed Grafana OIDC login and current Prometheus dashboard
     data in the browser on 2026-11-12.
   - [x] User validated a real Element audio/video call through MatrixRTC on
     2026-11-12. Tuwunel was cut over after stopping Ubuntu and validating an
     encrypted full data archive; public endpoints and SSO flow discovery pass.
     User confirmed post-cutover Element login, existing history, and message
     send. See the
     [service execution record](talos-service-migrations.md).
   - [x] Move Tuwunel after stopping the Ubuntu writer and verifying an
     encrypted archive of the complete data and backup trees. Public client,
     federation, discovery, and login-flow endpoints match the pre-cutover
     responses. Daily managed RocksDB backups and media/archive snapshots are
     enabled; the managed backup verification and archive integrity checks
     passed. A real post-cutover Element login, history check, and message send
     were confirmed by the user in Element.
   - [x] Move the stateless MatrixRTC LiveKit/JWT component to Talos `.74`;
     preserve Ubuntu ClusterIP and public ingress through selectorless bridges,
     then observe HTTP/WebSocket health. The user confirmed a real Element
     call before Tuwunel moved. See the
     [service execution record](talos-service-migrations.md).
   - [ ] Continue remaining services individually. See the
     [service execution record](talos-service-migrations.md).
   - [x] Move Homepage with the unchanged image and configuration; preserve
     its URL through the Ubuntu ingress bridge and pass a five-minute
     observation.
   - [x] Move Radarr with the existing Synology state and media paths, verify
     SQLite integrity, preserve Authentik routing, and pass a five-minute
     observation.
   - [x] Move Sonarr with the existing Synology config, downloads, and series
     paths; verify SQLite integrity, preserve Authentik routing, and pass a
     five-minute observation.
   - [x] Move qBittorrent with its existing Synology config, NymVPN state, and
     downloads; preserve Radarr/Sonarr DNS and Authentik routing, then pass a
     five-minute observation. Its Harbor pull secret still needs an Infisical
     source scoped to the `homelab` repository before rotation.
   - [x] Move NZBGet with its existing Synology config, NymVPN state, and
     downloads; preserve its authenticated UI, media service DNS, and HTTPS
     route, then pass a five-minute observation. It shares qBittorrent's
     outstanding Infisical registry-credential follow-up.
   - [x] User confirmed Vaultwarden login and vault synchronization after its
     PostgreSQL cutover. The final SQLite import, route checks, and observation
     passed.
   - [x] Add daily encrypted PostgreSQL and `/data` backups to an independent
     `nfs-k8s` PVC, retain 30 days, and restore a full backup on the
     workstation. The backup PVC shares the Synology failure domain with live
     data, so it does not replace an off-site copy.
   - [x] Deploy Portfolio on Talos with the identical production image digest,
     scoped registry credentials, separate RBAC, and verified local TLS.
   - [x] Restore its absent Pangolin resource, rehearse routing rollback to
     Ubuntu, switch to Talos, and stop the Ubuntu copy.
   - [x] Pass 606.8 seconds of public HTTPS/content observation after stopping
     Ubuntu Portfolio, with 58 healthy samples and no target Pod restarts.
     See [Portfolio migration](talos-portfolio-migration.md).
   - Start with a low-risk stateless application such as portfolio, then a
     service whose persistent data is easy to restore. Move dependency groups
     together only when required.
   - [x] Migrate Infisical to Talos without changing its application version;
     restore PostgreSQL, reuse its Synology NFS-backed Redis state, and
     validate public ingress plus Talos InfisicalStaticSecret reconciliation.
   - [x] Move Harbor to Talos with the same Harbor v2.15.4 images and chart
     version, rebind all five existing Synology NFS paths, sync secrets with a
     Talos-specific Infisical identity, and validate direct/public ingress, OIDC
     settings, and an authenticated registry manifest pull. Ubuntu writers remain
     stopped; the Ubuntu HTTPS ingress bridge stays in place for traffic.
   - [x] Observe direct Talos and Ubuntu-bridged HTTPS for 309 seconds across
     six healthy samples; all eight target Pods stayed Ready, the source stayed
     at zero Pods, and restart counts did not increase after startup.
   - [x] Move Hindsight on the same Synology NFS directory and exact production
     image digests; stop Ubuntu writers first, keep the Ubuntu Authentik outpost
     and HTTPS bridge, and pass six samples over five minutes. Authenticated browser
     validation showed the existing `hermes` bank and its memories.
   - [x] Move Job Search Manager and Garage after final stopped-writer backups;
     restore the final PostgreSQL dump, ensure one Garage writer on the shared
     NFS path, bridge the public HTTPS route, preserve its Authentik group
     binding, validate the browser data, and pass six samples over five minutes.
   - Keep Forgejo and Authentik available on Ubuntu until their separate
     migration windows. Use authentik.tom-mendy.com throughout.
   - For each service: prepare target without writers, suspend its Ubuntu GitOps
     reconciliation, stop all old writers and jobs, capture final data, restore
     or bind the target volumes, validate via Talos ingress, then switch traffic.
   - Prefer operator-supported restore for CloudNativePG. Do not treat reusing
     a PostgreSQL directory as a validated operator migration procedure.
   - Record old/new endpoints, image versions, PVC paths, backup checksums,
     write-stop time, cutover time, functional checks, and rollback deadline.
   - Observe one real usage cycle before the next service. Rollback after new
     writes requires recovering those writes or an explicit data-loss decision.
6. Convert node3. Status: workload moves pending; GPU installation prep complete.
   - Verify all remaining Ubuntu workloads have another eligible destination.
     node1 is currently tainted and is not a general application worker.
   - Kubelet sample on 2026-11-12: Ubuntu node3 had 8.08 GiB pod working set
     and 21.61 GiB node memory available; Talos node2 had 3.84 GiB pod working
     set and 10.77 GiB available. Current pod requests are 2.95 CPU / 5.88 GiB
     on Ubuntu node3 and 1.61 CPU / 2.60 GiB on Talos node2. Packing both
     current sets onto node2 would request 4.56 CPU against 3.95 allocatable;
     however, some Ubuntu system and GitOps pods will retire during conversion.
     Eighteen Talos and 33 Ubuntu containers have no memory request. Metrics API
     remains unavailable, so these samples do not establish peak capacity.
     Rebuild the per-workload placement model after remaining app migrations;
     do not drain node3 on these figures alone.
   - Plan Ollama/GPU downtime separately and validate the Talos GPU image and
     device plugin. A single GPU cannot fail over to a machine without one.
   - Talos v1.14.5 NVIDIA Image Factory schematic
     `af8eb82417d3deaa94d2ef19c3b590b0dac1b2549d0b9b35b3da2bc325de75f7`
     is prepared. It resolves the proprietary 580.178.04 driver and matching
     NVIDIA container toolkit 580.178.04-v1.19.1. The private node3 candidate
     passes strict v1.14.5 metal validation and still refuses installation:
     its disk selector is a placeholder and `wipe` is false. The current
     Ubuntu read-only inventory sees a GTX 1080 and several candidate disks;
     confirm NIC MAC and exact disk from maintenance mode before replacing
     the selector. The custom ISO is downloaded privately; SHA-256 is
     `c2b422673985da85bf9e991e1d353acd4ad257c560d7e4ceb3875fb0d1449cb9`.
   - The Talos v1.14.5 toolkit 1.19.1 runtime passed inference with the
     pinned Ollama workload on the GTX 1080.
     See the [Talos NVIDIA driver guide][talos-nvidia] and
     [Ollama hardware support][ollama-gpu].
   - Join node3 to the existing Talos cluster without another bootstrap.
     Two etcd voting members still require both members for quorum. Avoid
     maintenance and complete the third-member transition promptly.
7. Convert node1 and validate recovery. Status: joined, failure tests pending.
   - Keep the Ubuntu control plane until nothing depends on the old cluster.
   - Join node1 as the third Talos control plane. Verify API endpoint failover.
   - Test loss of one machine at a time, including node2-to-node3 and
     node3-to-node2 rescheduling of persistent workloads.
   - Keep backups until application-level recovery is validated. The Synology
     remains a shared failure domain even with three control planes.

[talos-nvidia]: https://docs.siderolabs.com/talos/v1.14/configure-your-talos-cluster/hardware-and-drivers/nvidia-gpu-proprietary
[ollama-gpu]: https://docs.ollama.com/gpu

The following evidence was collected on 2026-11-07 using context
`kubernetes-admin@cluster.local`. Private evidence and backups are stored at
`/home/tmendy/.local/state/homelab/talos-migration/20261107T102318Z/`.
This directory is outside Git and accessible only by its owner. It is on the
NixOS workstation, independent of the Kubernetes cluster and Synology. It is
not an off-site backup. Resource exports do not replace application backups or
an etcd snapshot. The Git bundle predates this tracker and needs refreshing
after the migration configuration is committed.

- All three nodes are Ready, running Kubernetes v1.34.3 on Ubuntu 24.04.5 LTS.
- There are 47 PVCs. None uses local-path. All Bound PVs use NFS and no PV has
  node affinity. `storage-bindings.json` records the current mapping. Historical
  July bindings are stale and must not be applied wholesale.
- The repository storage policy check passed. Existing documentation contains
  historical local-path migration instructions; those are not active workloads.
- Six healthy singleton CloudNativePG primaries run on node2: Authentik, Coder,
  Forgejo, Infisical, job-search-manager, and Open WebUI. All six PDBs allow zero
  disruptions. The July audit covered only two of these databases.
- node1 has the control-plane NoSchedule taint. Do not count its free memory as
  application capacity without a separate placement decision.
- node3 has approximately 30.44 GiB allocatable memory. Current worker requests
  total approximately 27.37 GiB, leaving about 3.07 GiB if consolidated onto
  node3 before accounting for removed node2 daemon pods. This is an estimate,
  not a scheduler simulation or a peak-load guarantee. Numerous services,
  including database instances, have no memory requests.
- Metrics API is unavailable. Read-only kubelet summary samples were collected
  instead. Working sets were approximately 7.91 GiB on node2 and 9.29 GiB on
  node3. One low-load sample does not establish maintenance safety. CI runners
  and Coder workspaces need a deliberate capacity plan before draining.
- job-search-manager PostgreSQL and object backup CronJobs report successful
  runs on 2026-11-07. Success status does not prove backup contents or restore.
- The November 2 maintenance report records database restore drills but also
  unresolved protection of encryption keys, independent backup copies, Garage,
  Hindsight, and corrupted Prowlarr backup contents. The old local path
  `/opt/data/maintenance-snapshots` is absent on this workstation. No contents
  of those historical archives were verified during this inventory.
- The old Talos preparation directory exists under
  `/home/tmendy/.talos/homelab-talos-2026-07-01`. Its sensitive contents were not
  printed or committed. Existence does not establish config validity or recovery.

Step 1 execution results:

- Six fresh custom-format pg_dump archives were captured from the CloudNativePG
  application databases on the workstation. Private `database-backups.json`
  records filenames, SHA-256 checksums, sizes, and restore results. These are
  online database snapshots, not final cutover backups or complete cluster-wide
  exports of roles and credentials.
- Coder, Forgejo, Infisical, and Open WebUI restored successfully into isolated
  local PostgreSQL 17 containers. They contain 130, 128, 795, and 48 application
  tables respectively. Owners and ACLs were omitted. No application, file,
  SSO, or Infisical decryption recovery is claimed by these tests.
- job-search-manager restored successfully into isolated local PostgreSQL 18
  with 11 application tables. All restore containers were removed afterwards.
- Authentik restore failed while creating the foreign key from
  authentik_tasks_tasklog to authentik_tasks_task. A read-only repeatable-read
  query against production found seven orphan log rows despite a validated
  constraint. This initial failure was resolved on 2026-11-07 by preserving the
  seven exact historical logs in a protected recovery archive and removing
  their invalid application references in one guarded transaction. No parent
  tasks were invented and all original constraints remain enabled. The failed
  dump and complete original logs are retained. See the
  [recovery record](authentik-tasklog-recovery.md) for evidence and checks.
- The fresh post-repair Authentik production dump passed a complete isolated
  PostgreSQL 17 restore with original object ownership and ACLs. All 230 public
  tables and the seven-row recovery archive restored; no public foreign key
  remained unvalidated and the integrity check passed. The test role had no
  login, so role-password, application-login, SSO, and external-file recovery
  remain outside this result. All six CNPG database dumps now have successful
  database restore tests. The broader recovery work is recorded below.
- A private standalone ubuntu.kubeconfig was created in the evidence directory.
  It contains credentials and must never enter Git. The original kubeconfig and
  default context were not changed. A Talos context awaits real cluster access.
- All three historical Talos configurations fail local validation because they
  define both a legacy static hostname and a HostnameConfig document. Candidate
  copies retain the static hostname and remove the conflicting HostnameConfig.
  All three candidates pass `talosctl validate --strict --mode metal` with the
  installed client. Original configurations are preserved. Schema validation
  does not validate hardware, version support, network reachability, or disks.
  The installation disk placeholder remains until physical disk inspection.
- The initial inventory did not cordon, drain, restart, or reinstall any node.
  The subsequent backup work temporarily paused selected service writers and
  reconciliation, then restored their replicas and reconciliation settings.
  The recovery record documents those operations and the Prowlarr repair.
- `rumdl check --fix .` ran and reported 147 existing issues in 22 files.
  It did not change tracked files. The new tracker is checked separately.

The missing application-backup work completed on 2026-11-07. See the
[backup and recovery record](talos-backup-recovery.md) for the verified database,
key recovery, Garage, Matrix, Redis, SQLite, repository, and file results.
The final private `manifest.json` records 55 encrypted archives and coverage or
explicit exclusions for 43 source volumes. All queued file archives passed
decryption and complete gzip readback. Harbor's 2,044 stored blobs and Ollama's
18 stored blobs matched their content-addressed SHA-256 filenames. Prowlarr's
repair preserved table data and produced a valid native backup. The Infisical
recovery key decrypted all 92 secret values from the restored database.

Recovery credentials and validated Talos candidate files are encrypted outside
the cluster. Bulk NAS media libraries and downloads are excluded except the
recorded NZBGet queue directories. This application recovery set is independent
of Synology, but is not off-site. UI/SSO and final cutover checks remain required.

The [node2 capacity plan](talos-node2-capacity.md) passes its static assessment
with CI runners, all three workspaces, Ollama inference, and bulk downloaders
paused for the full one-worker Ubuntu period. A 21.875 GiB workload budget plus
2 GiB system allowance and 4 GiB operational margin fits node3's 30.435 GiB,
leaving 2.560 GiB. Node1's taint remains unchanged. The plan checks placement,
portable storage, Pod count, init/sidecar requests, and historical memory peaks.
The six singleton CNPG PDBs still require separate relocation handling.
No workloads were stopped and no node was drained for this assessment.

The [Talos network preparation](talos-network-preparation.md) pins Talos v1.14.5
and Kubernetes v1.36.6. All three revised candidates pass strict validation with
the checksum-verified matching client. The new DNS-only API hostname is
`talos-api.home.tom-mendy.com`, resolving only to reserved VIP 10.0.0.65.
Ubuntu's live MetalLB pool was reduced to .60-.64 without changing Traefik .60
or Blocky .61. Talos reserves .70-.89 in a separate staged manifest outside
Ubuntu GitOps. The new candidates and recovery credentials passed encrypted
archive readback and per-file checksums. No Talos configuration was applied.
The installation disk remains unselected until physical ISO inspection, and
live VIP/API health and failover remain installation checks.

The [version-freeze preparation](talos-version-freeze.md) suspended both image
writers and both registry scanners and verified that their guards survive parent
reconciliation. The prior job-search-manager incident hold is preserved. Flux
was pinned to its unchanged deployed v2.9.6 release. No workload image reference
changed, and the final baseline drift check passed. CI drain, final Git-commit
pinning, immutable cutover images, and publisher controls remain window gates.

Step 1 completed during the explicitly authorized maintenance execution.
See [the node2 release record](talos-node2-release.md) for the isolated access
files, final Git baseline, CI and workspace holds, six database switchovers,
17 workload moves, and rollback state. At that pre-installation checkpoint,
node2 was cordoned, excluded from VIP announcements, and its kubelet was
stopped. Its disks were still untouched. The accepted
observation lasted 1,829.9 seconds, from 18:18:28 to 18:48:58 UTC, with every
sample healthy. The workstation sleep gap was excluded and the healthy timer
restarted after wake. Node1 and node3 are Ready; all retained services and six
database primaries are on node3. Two daily backup schedules are restored; the
capacity and application-update holds remain in place. Talos installation and
foundation checks subsequently completed on
2026-11-08. The next action is selective GitOps preparation in step 4.
Repeat each application's stopped-writer backup at its
actual cutover; these preparatory snapshots were taken at different times.

Storage rules for every subsequent operation:

- Use nfs-k8s for standard persistent application volumes backed by
  `10.0.0.11:/volume1/k8s`. Fixed existing Synology paths may use static NFS PVs.
- Rebind only the service being migrated, before its chart creates empty PVCs.
  Preserve exact NFS paths and set Retain before any destructive PVC operation.
- Never run writers from both clusters against the same application directory.
  ReadWriteOnce does not coordinate access between independent clusters.
- Never restore an application test over production data. Use isolated paths
  and prevent test instances from sending mail, jobs, or other external effects.
- Do not copy live database files as if they were a consistent backup. Use
  database-native backups or an application-specific quiesced procedure.

Related procedures: [storage](kubernetes-storage.md),
[backups](backup-procedures.md), [recovery](disaster-recovery.md),
[Flux bootstrap](flux-gitops.md), and
[November 2 backup evidence](activity_report/2026-11-02-application-upgrades.md).
