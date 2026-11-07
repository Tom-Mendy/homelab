# Capacity plan while node2 is unavailable

The 2026-11-07 read-only assessment passes for the restricted maintenance
profile below. It does not approve draining node2. Node1 retains its
control-plane NoSchedule taint and contributes no application capacity.
No workload was stopped, moved, restarted, or resized during this assessment.

Private evidence is under
`/home/tmendy/.local/state/homelab/talos-migration/20261107T154012Z-capacity/`.
`capacity-result.json` contains per-workload budgets, missing memory requests,
placement findings, and the PDB list. Raw workload exports may contain sensitive
configuration; keep this owner-only directory outside Git.

| Memory component | GiB |
| --- | ---: |
| node3 allocatable | 30.435 |
| Current combined worker requests | 27.401 |
| Remaining requests with the maintenance profile | 6.931 |
| Conservative workload budget with the profile | 21.875 |
| Additional system allowance | 2.000 |
| Operational margin for bursts and serial restarts | 4.000 |
| Unallocated after all allowances | 2.560 |

The profile has 67 projected Pods against node3's limit of 110, and 3.475 CPU
cores requested against 23.4 allocatable. Unrequested CPU and burst demand still
need observation. There are no HPAs in the captured cluster.

Memory budgets use the larger of declared requests, available historical
container working-set peaks multiplied by 1.25 and rounded up to 64 MiB, or
128 MiB per running container. Native sidecars are included. Effective scheduler
requests include init phases, restartable sidecars, and Pod overhead.
Historical metrics use a seven-day query lookback, not a guarantee of seven
complete days of samples. Restarted Pod names are grouped by current controller.
The sum of individual peaks is conservative and is not a simultaneous observed
cluster peak. The system allowance and burst margin are planning choices.

Many retained containers have no memory request. Their measured budgets are
included instead of treating them as free. This assessment does not add resource
requests or limits and does not trigger application rollouts. CPU requests are
not CPU peak measurements, and memory budgets are not enforced ceilings.
Schedule permanent request sizing separately after the migration baseline is
stable; until then, prohibit new workload growth during maintenance.

Pause these workloads for the entire period that Ubuntu has only node3 as an
application worker, not just during the drain command:

| Namespace | Target | Maintenance state |
| --- | --- | --- |
| forgejo-runner | forgejo-runner-buildkit | 0 replicas after jobs finish |
| forgejo-runner | forgejo-runner-homelab | 0 replicas after jobs finish |
| forgejo-runner | forgejo-runner-job-search-manager | 0 replicas after jobs finish |
| forgejo-runner | forgejo-runner-portfolio | 0 replicas after jobs finish |
| arc-runners | arc-runner-set-dotfiles | minRunners 0, maxRunners 0 |
| arc-runners | arc-runner-set-sumfleet-tom | minRunners 0, maxRunners 0 |
| coder-workspaces | Desktop | Stopped through Coder |
| coder-workspaces | Hermes | Stopped through Coder |
| coder-workspaces | T3 | Stopped through Coder |
| ollama | Deployment ollama | 0 replicas; inference unavailable |
| media | Deployment qbittorrent | 0 replicas; downloads paused |
| media | Deployment nzbget | 0 replicas; downloads paused |

The four Forgejo runners reserve 12.25 GiB, and the three workspaces reserve
8 GiB plus T3's 32 MiB settings sidecar. GitHub's normal maxima are five dotfiles
and ten sumfeet runners, even when no runner Pod currently exists.
Ollama's available historical host-memory peak is about 15.8 GiB, and
qBittorrent's about 2.7 GiB. The conservative assessment still fails when only
CI and workspaces are paused. Inference and bulk download pauses are required
for this profile. Keep Open WebUI, its database, Coder's control plane, Hindsight,
and the core application services running. Hindsight batch work, Harbor scans,
large imports, and builds must wait until capacity is restored.

Stopping Hermes also stops its Matrix agent gateway. T3's runtime is ephemeral;
export unfinished sessions before stopping it. Preserve all workspace PVCs and
stop workspaces through Coder rather than deleting them. Run the maintenance
from the independent NixOS workstation, not from a workspace being stopped.
If these pauses cannot be sustained, use an additional Ubuntu worker or revise
and revalidate the profile before releasing node2. Do not remove node1's taint
as an unplanned substitute.

Apply the profile only in the maintenance window, in this order:

1. Save original replicas, runner bounds, CronJob suspend flags, HelmRelease
   suspend flags, Coder workspace states, and the Flux Kustomization suspend
   state in a new private evidence directory. Do not assume the November values
   are still current. Preserve this resume record outside Kubernetes.
2. Protect temporary settings from reconciliation. The live parent is
   `Kustomization/flux-system` in `flux-system`; suspend it before changing
   the relevant HelmRelease suspension flags. Suspend all four
   `forgejo-runner-*` releases, `github-runners-dotfiles`,
   `github-runners-sumfeet`, `media`, and `ollama` before their temporary
   replica or runner-bound changes. Suspending only a HelmRelease is insufficient
   if its parent can overwrite that flag. Keep runtime operators running.
3. Block CI intake for the affected repositories and let running jobs finish.
   Set both GitHub pool bounds to zero and wait for their ephemeral runner Pods
   and Jobs to finish. Do not kill builds by scaling a busy Forgejo runner.
   GitHub documents this zero-bound drain in its
   [ARC scale-set procedure][arc]. Keep ARC's controller and listeners running.
4. Stop the three workspaces through Coder, then pause the listed Deployments.
   Suspend the two job-search-manager backup CronJobs and
   `ollama/openwebui-function-sync`, and let existing Jobs finish. Take final
   backups before the pause where needed. Suspend scheduled work temporarily;
   do not delete backup schedules or disable backup protection permanently.
5. Confirm every listed target is stopped, no CI jobs remain active, both ARC
   pools have zero bounds, and no workspace autostart can reverse the pause.
   Wait for terminating Pods too. Re-run the read-only capture below.
6. Relocate workloads individually using the separate database maintenance
   procedure. All six CNPG primary PDBs currently allow zero disruptions.
   A successful capacity check does not bypass them. Do not run a blanket drain
   with eviction protections disabled. Avoid simultaneous database restarts.
7. Before erasing node2, observe the evacuated Ubuntu cluster under normal
   retained-service activity for at least 30 minutes. Require all retained
   workloads Ready, no unexpected Pending Pods, no new OOM kills, no node
   MemoryPressure or DiskPressure, working NFS, DNS, ingress, database access,
   and the retained-service functional checks. Recompute the budget with node2
   empty. Keep at least 4 GiB of measured node3 memory availability throughout;
   stop and investigate if it falls below that floor or keeps declining.

If the pre-erasure rehearsal fails, stop the evacuation, restore scheduling on
node2, and recover retained services before restoring optional load. Resume only
the saved states that are safe for the available capacity. After node2 is Talos,
do not restore all Ubuntu CI and workspaces to this one-worker profile. Restore
them individually only after another eligible Ubuntu worker exists or their
target Talos capacity and service dependencies have been validated. Restore
CronJobs, runner bounds, workspace states, replica counts, and reconciliation
from the saved record, then verify that queued CI jobs actually run.

To refresh the assessment without changing the cluster:

```sh
python3 scripts/check-node2-capacity.py --capture \
  --context kubernetes-admin@cluster.local \
  --evidence /private/new-capacity-evidence
```

Exit zero means the projected profile fits the implemented static checks.
`window_ready` deliberately remains false because the script does not apply
pauses, execute a real scheduler replay, or authorize database evictions.
Review the private report and apply the maintenance gates explicitly.
The command can also recheck an existing evidence directory without `--capture`.

Required selectors, node affinity, taints, host ports, Pod count, requested
resources, and mounted-PVC portability were checked. Hard inter-Pod affinity or
hard topology-spread rules cause a review failure instead of being ignored.
CNPG anti-affinity and portfolio spreading are preferences, so they do not
prevent consolidation. Every retained bound PVC uses Synology NFS and has no
PV node affinity. DaemonSets and mirrored host Pods on node2 are not duplicated
onto node3. SearXNG's hostPath is the `/dev/net/tun` character device, already
used on node3, rather than persistent application data.

Regression checks rejected the unrestricted profile, CI/workspace-only pauses,
and an untolerated node3 taint. Unit checks cover init and sidecar resource
accounting and hard placement constraints. Static evidence cannot establish
performance under every load; the pre-erasure observation remains mandatory.

See [the migration tracker](talos-migration.md) and
[backup recovery](talos-backup-recovery.md). Kubernetes documents
[resource scheduling][resources] and [sidecar request accounting][sidecars].

[arc]: https://docs.github.com/en/actions/how-tos/manage-runners/use-actions-runner-controller/deploy-runner-scale-sets
[resources]: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
[sidecars]: https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/
