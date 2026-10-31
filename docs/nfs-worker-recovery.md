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
