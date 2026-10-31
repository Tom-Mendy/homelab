# NFS worker recovery

## Diagnosis

A client can retain revoked NFSv4 delegation state after a NAS restart. Compare
both workers rather than downgrading the protocol or increasing application
probe timeouts. The observed signature is a sustained `TestStateID` request
storm, slow read/write file opens, and normal cached read-only file access.

On 2026-10-31, a bounded packet capture on node3 decoded 21,894 SEQUENCE replies;
all carried status flags `0x40` (`SEQ4_STATUS_RECALLABLE_STATE_REVOKED`). No file
contents or packet capture were retained. The flag definition is in Linux
[`include/uapi/linux/nfs4.h`](https://github.com/torvalds/linux/blob/v6.8/include/uapi/linux/nfs4.h).
This confirms the protocol symptom, not which client/server version contains
the software defect.

## Independent recovery controller

Run the controller on node2, never inside a shell that will disappear when
node3 is drained. The current Hermes workspace is on node3 before recovery.
Maintenance accepts downtime for single-instance applications. PostgreSQL PDBs
are deliberately bypassed by graceful pod deletion, not force deletion.

```bash
python3 scripts/render-nfs-recovery.py | kubectl apply -f -
kubectl -n nfs-maintenance logs job/nfs-worker-recovery
kubectl -n nfs-maintenance get configmap nfs-worker-recovery -o jsonpath='{.data}'
```

This only prepares the controller. Before approval:

- Verify node2 has room for the controller and the Hermes workspace. Other
  workloads may remain Pending until node3 returns; do not remove requests or
  relax security constraints to make them fit.
- Verify the configured image can run on both workers, that its `chroot` exists,
  and that `/usr/bin/systemctl` exists on the worker.
- Inspect the healthy workload baseline and preserve known pre-existing errors.
- Confirm backup/recovery access, persistent PVC/PV identities, and that the
  user accepts maintenance interruptions. Save active interactive work.
- Ensure no unmanaged diagnostic pods are left on node3. The controller refuses
  to delete unmanaged pods; it skips DaemonSets and static mirror pods.
- Arrange a durable follow-up to check the controller after Hermes relocates.

Explicit approval:

```bash
kubectl -n nfs-maintenance patch configmap nfs-worker-recovery --type=merge \
  -p '{"data":{"execute":"true"}}'
```

The controller cordons node3, moves Hermes to node2 and waits for readiness,
then gracefully deletes the remaining managed application pods. It preserves
each configured termination grace period and refuses to reboot if any remain.
Only then does a temporary privileged pod request a host systemd reboot. It
never changes NAS settings, protocols, PVCs, databases, or SSH keys.

The reboot pod temporarily has host-root access; its service account token is
not mounted. The independent controller has no Secret access and uses a
projected, short-lived token. Do not retain these maintenance permissions.

Success requires a new boot ID, Ready status, restored scheduling, recovery of
the previously healthy Deployment/StatefulSet baseline, and a low TestStateID
rate after workloads return. Also verify the per-worker synthetic file-access
probe, Coder agents, database health, Authentik and Matrix. A reboot alone is
not proof of recovery.

If a graceful drain fails, the controller restores scheduling and stops. If a
requested reboot fails, the worker remains cordoned for operator inspection.
It never force-deletes a stuck database or retries reboot indefinitely.

## Verified recovery on 2026-10-31

The independent controller completed successfully: node3 obtained a new boot
ID, resumed scheduling, restored all 64 previously healthy controllers and
reported **0 TEST_STATEID/s**. All three nodes were Ready and all six CNPG
clusters healthy. Authentik and all three Coder workspaces returned.

A 48-open read/write benchmark, without modifying file contents, measured:

| Workspace | Before p95 | After reboot p95 |
| --- | ---: | ---: |
| Hermes | 79.729 ms | 0.767 ms |
| T3 | 75.564 ms | 0.592 ms |
| Desktop | 0.795 ms | 0.701 ms |

These measurements precede the separate, user-requested T3 storage migration.
T3 subsequently moved to a 1Gi settings-only NFS claim with an ephemeral home.
Only 77 allowlisted configuration/authentication files (371,115 bytes) were
copied; no projects, runtimes, applications or SQLite databases. A real Pod
replacement preserved three checked settings files and Codex authentication,
discarded a disposable project fixture and returned HTTP 200 on port 3773.
The former T3 PV is retained as a temporary rollback source, not a live backup
of future projects. Workspace PVC requests total 31Gi of the 40Gi quota.

Controller logs/status were exported under `/opt/data/reports`, and the
temporary maintenance namespace, ClusterRole and ClusterRoleBinding were
removed after health checks. The change-only NFS watchdog remains enabled;
NFS rule/probe installation has its own rollout verification gates in
[`NFS-MONITORING.md`](../kubernetes/prometheus/NFS-MONITORING.md).

## Remaining Coder publication credential gate

The live T3 migration and Pod-replacement test succeeded. Its source is committed,
but the active Coder template remains `daily-cli-installers-20261027` until
publication completes. Forgejo validation passed; publication was first blocked
by a TLS reset downloading `coder.com/install.sh`. The replacement official-release
installer was exercised locally and in CI, with SHA-256 verification, successfully.
The remaining CI error is an unset repository Actions `CODER_SESSION_TOKEN`.
Do not bypass Coder authentication through database changes. An authorized
operator must configure the dedicated token securely and rerun the publisher.
Do not rebuild T3 from the old full-home template before activation is verified.

## Separate unresolved SQLite compatibility

Do not interpret client recovery as SQLite WAL becoming supported on NFS.
The current installed Hermes source re-enables WAL and does not implement the
[new documented `database.journal_mode`](https://hermes-agent.nousresearch.com/docs/user-guide/configuration#database-settings)
or the offline `hermes sessions set-journal-mode` command. A synthetic-only
source test confirmed that converting to DELETE alone is undone on open.
`verification_evidence` and the Matrix crypto store also explicitly request WAL.
Even upgrading to an image that supports the setting requires checking those
additional database owners, especially Matrix, before claiming NFS compatibility.

Preparation requires a supported image first, then coordinated writer shutdown
across all NFS clients, a coherent backup, integrity checks, supported offline
conversion and verification after restart. No live journal conversion, WAL/SHM
deletion or runtime monkeypatch was performed. No corruption was demonstrated.
T3's disposable SQLite stores now remain outside NFS, independently of Hermes.

## Cleanup

After exporting the controller logs/status and completing application checks:

```bash
kubectl -n nfs-maintenance logs job/nfs-worker-recovery
kubectl -n nfs-maintenance get configmap nfs-worker-recovery -o jsonpath='{.data}'
kubectl delete clusterrolebinding nfs-worker-recovery
kubectl delete clusterrole nfs-worker-recovery
kubectl delete namespace nfs-maintenance
```

The helper creates no persistent volume and copies no credentials. Keep the
shared NFS storage policy. Do not convert SQLite journal modes while processes
are using the database, remove live WAL/SHM files, or use worker-local durable
storage as a shortcut.
