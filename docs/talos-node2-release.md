# Node2 release and ISO handoff

Execution completed on 2026-11-07. Application evacuation and the required
observation passed. Node2 is ready for manual ISO boot and disk inspection.
Talos installation and bootstrap have not been performed.

Private evidence, access files, backups, and original maintenance settings are at
`/home/tmendy/.local/state/homelab/talos-migration/20261107T165551Z-node2-release/`.
Keep this owner-only directory outside Git. Raw exports contain credentials.
The approved Ubuntu Git baseline is
`4b00ce07c4c4ebea0817ff5a64eae462caf23e35`.

The Ubuntu source is fixed to that commit. Its generating FluxInstance is held,
the root Kustomization is suspended, and all 41 HelmReleases are held for this
maintenance window. Runtime operators and workload controllers remain running.
The earlier image automation holds and exact Flux v2.9.6 pin remain in place.
`maintenance-state.json` records the original flags and refs for restoration.
An updated external Git recovery bundle was created and verified.

Both GitHub runner pools have minRunners and maxRunners set to zero. Forgejo
Actions intake is disabled for `Tom-Mendy/homelab`, `Tom-Mendy/Portfolio`, and
`Tom-Mendy/job-search-manager`; their previous settings are recorded. All four
Forgejo runner Docker daemons had zero running job containers before their
Deployments were scaled down. No running build was killed to free capacity.
The existing Forgejo action-run history remains present.
A repository-scoped maintenance token named
`talos-node2-maintenance-20261107` was created for these settings and retained
privately for recovery. Revoke it after Actions settings have been restored.

Desktop, Hermes, and T3 were stopped through Coder, with autostart schedules set
to manual. Their three original PVC/PV bindings remain Bound and unchanged.
An external client restarted T3 once after the first stop. A temporary
`ResourceQuota/talos-node2-maintenance-hold` in `coder-workspaces` now sets
`pods: 0` to block further workspace starts. T3 was stopped again. This hold
does not delete PVCs. A client may report a failed or blocked start while it is
active; remove it only when workspace capacity is restored.

T3's ephemeral `.t3`, `.codex`, OpenCode, and SSH state was checkpointed before
stopping it. SQLite databases were backed up through SQLite's backup API.
The encrypted checkpoint passed byte checks, full archive readback, and database
integrity checks. Runtime symlinks are retained as archive metadata but were not
followed during the recovery test. Restore application state deliberately and
recreate runtime links from the workspace image rather than blindly following
absolute links. The checkpoint is `t3-ephemeral-checkpoint.tar.gz.age` in the
private evidence directory.
For later recovery, put durable user state on the shared Synology NFS-backed
storage rather than making it depend on a worker's ephemeral runtime directory.

Ollama inference, qBittorrent, and NZBGet are scaled to zero. The three CronJobs
were held during observation. Afterwards, the two staggered daily
job-search-manager backup schedules were restored to their original active
states; both use Forbid concurrency and have no node2 placement constraint.
Open WebUI's application-function sync remains suspended. Keep the remaining
capacity restrictions for the entire period that node3 is the only Ubuntu
application worker. Open WebUI remains available, but local Ollama inference and
the Hermes agent gateway are intentionally unavailable during this profile.

The six database moves used the operator-supported temporary-replica procedure
described in the [CloudNativePG maintenance guide][cnpg]. For each cluster:

1. Capture a fresh custom-format dump and verify complete pg_restore readback.
   Verify the transferred bytes and an encrypted decryption round trip.
2. With node2 cordoned, increase instances from one to two. Wait for the operator
   to create the replica on node3 and switch the primary there.
3. Require both instances Ready, the same database system identifier, replay of
   the saved WAL checkpoint, the same public-table count, and application
   readiness before reducing instances back to one.
4. Wait until the remaining primary is healthy on node3 and the old Pod is gone
   before moving the next database. Preserve the original NFS data and Retain
   reclaim policies. Never disable PDB management or force all evictions.

| Namespace | Cluster | Current primary on node3 |
| --- | --- | --- |
| ollama | openwebui-postgres | openwebui-postgres-2 |
| job-search-manager | job-search-manager-postgres | job-search-manager-postgres-2 |
| coder | coder-postgres | coder-postgres-2 |
| authentik | authentik-postgres | authentik-postgres-2 |
| infisical | infisical-postgres | infisical-postgres-2 |
| forgejo | forgejo-postgres | forgejo-postgres-2 |

All six returned to one healthy instance. Their six primary PDBs remain managed
and allow zero voluntary disruptions, as before. The fresh encrypted dumps and
individual relocation results are retained in the evidence directory. No old
database volume was manually purged or reused as a separate writer.
Authentik's read-only task/log integrity check also passed on its new primary.

Seventeen other retained workloads were moved individually. The CNPG operator,
Hindsight and its control plane, Atuin PostgreSQL, Infisical Redis and API,
Radarr, Sonarr, MetalLB controller, NFS provisioner, kube-state-metrics, and the
six Flux components now run on node3. Every moved container was pinned to its
observed runtime digest and checked for identical image content after relocation.
Stateful writers used Recreate or serial StatefulSet replacement. Radarr and
Sonarr's previous rolling-update strategies were corrected to Recreate in the
live objects and chart templates to prevent overlapping SQLite writers.

Infisical briefly became unready during the Redis restart. The sequence stopped
at that gate, verified its recovery, and then continued. Its container did not
restart during that transient. Other application moves were not run concurrently
with the database switchovers.

Node2 is cordoned and has no active application Pods. Its kubelet was stopped
through systemd after evacuation, so its Ubuntu node status becomes Unknown or
NotReady. This is intentional. The machine remains powered on, SSH remains
available for rollback, and no disk was repartitioned, wiped, or reinstalled.
Some old DaemonSet/mirror containers may remain until reboot; they do not host
the retained application services.

Node2 is excluded from external load balancer announcements. Both .60 and .61
are announced by node3, and workstation ARP entries identify node3's physical
MAC for both VIPs. `kube.home.tom-mendy.com` was moved from .22 directly to node1
at 10.0.0.21 so Ubuntu administration does not depend on node2's API proxy.
The separate Talos API hostname still resolves only to reserved VIP .65.

The observation supervisor checks every 30 seconds:

- Node1 and node3 readiness and pressure conditions, with node2 still out of
  worker service and empty of application Pods.
- A minimum of 4 GiB available memory on node3, Pod/controller readiness, and
  new OOM terminations.
- All six primary database roles and SQL queries, six dependent application
  health endpoints, and Radarr, Sonarr, and Hindsight functional health checks.
- Fresh NFS read/write/fsync probe results, Blocky DNS answers, canonical
  Authentik HTTPS readiness at `authentik.tom-mendy.com`, and node3 ownership
  of both application VIPs.

`observation-samples.jsonl` contains the samples and `observation-progress.json`
contains the current verdict. A failed check resets the uninterrupted healthy
timer. Only `observation-result.json` with `status: complete` and at least
1,800 stable seconds closes this gate. This is observation under the restricted
maintenance profile, not a peak-load or node3-failure test.
One earlier probe failed when the NixOS workstation suspended and lost its
network. The system suspend journal confirms the cause. The gap was excluded,
the healthy timer restarted at 18:18:28 UTC, and a temporary sleep inhibitor
protected the remainder of the observation. It is removed at handoff.

The accepted window ran from 18:18:28 to 18:48:58 UTC on 2026-11-07, lasting
1,829.9 seconds. Every sample in that uninterrupted window was healthy. The
minimum available node3 memory across collected healthy samples was 17.569 GiB,
above the 4 GiB floor. Node1 and node3 remained Ready, all six databases answered
as primaries on node3, NFS checks passed, and node2 hosted zero application Pods.
`handoff-result.json` records `ready-for-manual-iso-inspection`.

`node2-release-recovery.tar.gz.age` protects the access credentials, original
settings, execution scripts, metadata, and rollback evidence. All 198 members
were compared byte-for-byte after decryption, then full gzip readback passed.
`release-artifacts.json` indexes that archive, the six fresh database dumps,
T3's session checkpoint, and the boot ISO. The existing separate age recovery
identity is unchanged. Keep this set alongside the earlier application backups.

Use the isolated access files explicitly:

```sh
kubectl --kubeconfig /private/node2-release/access/ubuntu.kubeconfig \
  --context ubuntu-homelab get nodes
```

The actual files are in `access/` under the evidence directory. Ubuntu uses
10.0.0.21 and its existing CA and administrator credentials. The global
kubeconfig and default context were not changed.
`talos-pending.kubeconfig` contains the separate Talos CA, VIP endpoint, and
`talos-homelab` context, with an exec credential helper that deliberately fails
closed until bootstrap. It is not working Talos Kubernetes authentication.
`access/talosconfig` is the separate Talos management configuration, targeting
node2 directly at 10.0.0.22. Use the previously checksum-verified v1.14.5 client
from the [network preparation](talos-network-preparation.md).
The matching ISO is downloaded at `boot/talos-v1.14.5-metal-amd64.iso` under the
evidence directory, with its SHA-256 file alongside it. Byte-range lengths and
the ISO filesystem identifier were checked; `boot-iso.json` records its source,
size, and checksum. No USB or installation disk was written by this execution.

After the observation passes, the next action belongs to the physical operator:

1. Boot node2 using the prepared Talos v1.14.5 ISO and confirm its identity,
   wired NIC MAC, disk model, serial, and capacity from maintenance mode.
2. Create a separate final reviewed copy of the node2 candidate. Replace the
   nonmatching installation disk selector only after that inspection, then
   validate with the matching client. The preparation files still refuse an
   unconfirmed installation target.
3. Apply that reviewed configuration and bootstrap the new cluster once using
   the direct node2 management address. This execution did neither action.
4. Retrieve a real Talos Kubernetes kubeconfig into a new private file, rename
   its actual context to `talos-homelab`, and validate the target CA, VIP endpoint,
   TLS, and `/readyz` using the pinned Kubernetes v1.36.6 client. Keep Ubuntu's
   access file and default context unchanged. Do not substitute Ubuntu credentials.
5. Validate target CNI, NetworkPolicy enforcement, DNS, NFS persistence, ingress,
   reboot recovery, and selective GitOps before migrating any production service.
   Retire node2's stale Ubuntu Node object only after the Talos installation is
   confirmed and rollback to Ubuntu is no longer required.

For rollback before installation, start node2's kubelet over SSH with
`sudo systemctl start kubelet`, wait for Ready, restore its original load-balancer
exclusion label state, and uncordon it using the explicit Ubuntu context.
Verify retained applications first. The new primaries and current PVCs remain
authoritative; never launch an old retained database directory as a second
primary. Restoring scheduling does not require restoring stale database data.

Then restore only the saved maintenance settings that fit the available capacity:
the repository Actions flags, runner bounds/replicas, workspace schedules and
states, paused Deployments, and CronJob flags. Remove the workspace quota before
deliberately starting workspaces. Restore Helm/Git/FluxInstance reconciliation
from `maintenance-state.json` only after reviewing current Git against the live
image pins and Recreate fixes. Keep the earlier job-search-manager incident hold
and exact Flux version pin. The [version-freeze procedure](talos-version-freeze.md)
has its separate original image-automation resume record.

After node2 has been erased, do not run that Ubuntu worker rollback or resume all
optional load on node3. Keep the holds until capacity is restored or the affected
workloads are deliberately migrated to Talos. No automatic thaw is scheduled.

See [the migration tracker](talos-migration.md) and
[the restricted capacity profile](talos-node2-capacity.md).

[cnpg]: https://cloudnative-pg.io/docs/1.27/kubernetes_upgrade/
