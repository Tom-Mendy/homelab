# Agent Instructions

## Storage policy

`local-path` is forbidden for Kubernetes workloads in this repository.

The cluster must be able to survive the loss or shutdown of any worker node,
including `node3`, without stranding persistent application data on that node.
Do not add manifests, Helm values, documentation, or operational procedures that
make a stateful workload depend on a worker-local disk.

Use the shared NFS-backed Kubernetes storage class for standard persistent
volumes:

```yaml
storageClassName: nfs-k8s
```

The approved backing store is the Synology NFS export at `192.168.1.1`, rooted
at `/volume1/k8s`. Workload data should be isolated by namespace/application/PVC
subdirectories managed by the NFS provisioner.

Static NFS PVs are acceptable only when a workload needs a fixed pre-existing
path, such as a media library. Those PVs must use Synology NFS, must not use
node affinity, and must use a non-local `storageClassName` or an empty
`storageClassName`.

## Exceptions

Do not grant exceptions for ingress, DNS, GitOps, monitoring, databases,
application config, user data, or any service needed to recover the cluster.

A temporary exception must include all of the following in the same change:

- A clear comment marking it as temporary.
- A migration issue or follow-up task.
- A reason NFS-backed storage cannot be used yet.

## Review checklist

Before finishing Kubernetes changes:

- Run `./scripts/check-storage-policy.sh`.
- Confirm no active manifest under `kubernetes/` uses `local-path`.
- Confirm new persistent workloads can reschedule from `node2` to `node3` and
  from `node3` to `node2`.
- Prefer S3-compatible storage only for object data, artifacts, and backups. Do
  not use S3 as a general POSIX PVC replacement.

## Learning and Kubernetes activity reports

The repository owner is currently learning Kubernetes and homelab operations.
For every significant activity performed through Kubernetes, write an activity
report under `docs/activity_report/`.

to check markdown quality use:

```sh
rumdl check --fix .
```

Use one Markdown file per activity, with a dated and descriptive name such as
`2026-05-14-migrate-grafana-pvc.md`.

Each report must include:

1. The problem that had to be solved.
2. The reasoning path used to solve it, including the commands to run.
3. The command results, including commands that failed but helped move the
   investigation forward.
4. The final outcome and what had to be changed.

Prefer concrete command transcripts and observed outputs over summaries when the
details are useful for learning later.
