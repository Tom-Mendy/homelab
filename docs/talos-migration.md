# Talos migration tracker

Last updated: 2026-11-11. This file is the migration progress record.
Steps 1 and 2 are complete. Talos v1.14.5 is installed and bootstrapped on
node2 (Kubernetes v1.36.6, node Ready). Step 3 foundation validation is
complete, including Cilium NetworkPolicy enforcement, DNS, isolated NFS,
MetalLB, HTTPS ingress, and recovery after reboot. Step 4, selective GitOps,
has a validated restricted bootstrap. Production applications remain on Ubuntu.

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
   - [ ] Prepare application-specific credentials, operators, target ingress,
     and the first production traffic cutover.
   - Use an explicit Talos application allowlist. Do not reconcile the complete
     production application tree into the new cluster.
   - Prepare an external Git bootstrap source or temporary reachable Ubuntu
     Forgejo endpoint. Prepare Infisical credentials for the new Kubernetes identity.
   - Replace temporary cross-cluster service dependencies with reachable
     endpoints. Cluster-local service names do not span clusters.
5. Migrate applications individually. Status: Portfolio, Cinny, Navidrome,
   SearXNG, and Homepage complete.
   - [x] Move Cinny with its unchanged image and homeserver, verify routing
     rollback, and observe public HTML/config plus Matrix discovery.
   - [x] Move Navidrome after native SQLite/file recovery checks, preserve
     users/playlists/shares, and pass a five-minute observation.
   - [x] Create the separate Talos Infisical identity, synchronize both
     SearXNG Secrets, preserve the stopped-writer NymVPN state, and verify
     connected Swiss egress and five-minute routing stability. See the
     [admin handoff](talos-infisical-admin-handoff.md) and
     [service execution record](talos-service-migrations.md).
   - [ ] Continue remaining services individually. See the
     [service execution record](talos-service-migrations.md).
   - [x] Move Homepage with the unchanged image and configuration; preserve
     its URL through the Ubuntu ingress bridge and pass a five-minute
     observation.
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
   - Keep Forgejo, Infisical, and Authentik available on Ubuntu until their
     separate migration windows. Use authentik.tom-mendy.com throughout.
   - For each service: prepare target without writers, suspend its Ubuntu GitOps
     reconciliation, stop all old writers and jobs, capture final data, restore
     or bind the target volumes, validate via Talos ingress, then switch traffic.
   - Prefer operator-supported restore for CloudNativePG. Do not treat reusing
     a PostgreSQL directory as a validated operator migration procedure.
   - Record old/new endpoints, image versions, PVC paths, backup checksums,
     write-stop time, cutover time, functional checks, and rollback deadline.
   - Observe one real usage cycle before the next service. Rollback after new
     writes requires recovering those writes or an explicit data-loss decision.
6. Convert node3. Status: not started.
   - Verify all remaining Ubuntu workloads have another eligible destination.
     node1 is currently tainted and is not a general application worker.
   - Plan Ollama/GPU downtime separately and validate the Talos GPU image and
     device plugin. A single GPU cannot fail over to a machine without one.
   - Join node3 to the existing Talos cluster without another bootstrap.
     Two etcd voting members still require both members for quorum. Avoid
     maintenance and complete the third-member transition promptly.
7. Convert node1 and validate recovery. Status: not started.
   - Keep the Ubuntu control plane until nothing depends on the old cluster.
   - Join node1 as the third Talos control plane. Verify API endpoint failover.
   - Test loss of one machine at a time, including node2-to-node3 and
     node3-to-node2 rescheduling of persistent workloads.
   - Keep backups until application-level recovery is validated. The Synology
     remains a shared failure domain even with three control planes.

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
