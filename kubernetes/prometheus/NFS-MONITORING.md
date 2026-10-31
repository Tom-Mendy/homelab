# NFS recurrence monitoring

## Deployment boundary

The upstream `prometheus` HelmRelease uses chart **29.36.1** and consumes
`values.yaml` through the generated `prometheus-values` ConfigMap. Its
`serverFiles.alerting_rules.yml` is loaded by the chart's default `rule_files`.
The separate `prometheus-extras` HelmRelease renders the local scratch PVC,
script ConfigMap and worker DaemonSet. Both releases must reconcile the same
Git revision; no Prometheus Operator or `PrometheusRule` CR is involved.

Alertmanager remains disabled. The existing script-only Hermes cron running
`/opt/data/scripts/homelab-nfs-watchdog.py` provides actual Matrix notification
for TEST_STATEID recurrence and forwards firing `NFS*` rules from Prometheus,
including synthetic checks, after two consecutive faulty observations.
Notifications and recovery messages are change-only, with a five-minute polling
interval. No additional messaging token is copied into the cluster. Do not
enable an empty receiver or treat the homeserver as an Alertmanager webhook.
A healthy read verifies the integration; actual failure-message delivery must
be verified separately without inventing a production storage fault.
Prometheus and the Hermes watchdog also depend on NFS: total NAS loss needs
an independent external monitor.

## Probe budget and safety

- One pod per eligible Linux worker, excluding control-plane/master role
  labels; no worker-role label is required. No host mount, application PVC,
  API token, root process, added capability or privileged init container.
- Dedicated RWX `nfs-probe-scratch` PVC, dynamically provisioned with `nfs-k8s`.
  Each node/pod UID gets its own private directory. The NFS child validates
  the deepest mount is NFSv4.1 before accessing scratch.
- Initialize **32 × 4 KiB = 128 KiB per pod UID**, once. Every 60 seconds,
  perform three passes (96 samples) of writable OPEN, content-validated read,
  CLOSE, **without rewriting fixtures**. This intentionally exercises NFSv4
  writable-open state rather than just a warm read-only benchmark.
- Export nearest-rank batch p95 in seconds, success, sample count, last-result
  and last-success timestamps, timeout count and blocked-child status. A failed
  batch removes latency rather than publishing old p95 as fresh success.
- All mount/filesystem work runs in one child. At 20 seconds, the parent sends
  SIGKILL without waiting. HTTP remains available and no replacement child is
  started until that child has actually exited. Hard-mounted NFS can keep a
  killed child in kernel sleep; **the deadline does not guarantee kernel I/O
  cancellation or bounded pod termination**. Health probes only check HTTP.
- No recursive `fsGroup` change or root permission-fixing container is used.
  The provisioned scratch root must allow UID/GID 65534 to create a directory
  (the normal NFS provisioner directory permissions). A permission problem is
  reported as failed storage checks, not fixed by touching application data.
- Old pod-UID directories are not automatically removed: periodically remove
  only confirmed inactive directories from this dedicated scratch claim.
  Each restart adds 128 KiB until cleanup. Never clean an application PVC.

## Rules

`NFSTestStateIDStorm` requires >100 requests/s **and** >50% of all client NFS
operations for 10 minutes, by node, using only the verified
`kubernetes-service-endpoints` job and `TestStateID` method spelling.
Additional alerts cover p95 >10 ms for 10 minutes, failed checks for 2 minutes,
results older than 180 seconds for 2 minutes, missing/down scrapes for 2 minutes,
missing client counters and incomplete/absent DaemonSet coverage for 5 minutes.
These are starting thresholds, not application-wide latency guarantees.

## Offline validation

Requires Helm, Python with PyYAML, and `promtool` (validated with 3.5.0).
Run from the repository root; keep downloaded artifacts outside the repository:

```sh
helm pull prometheus --repo https://prometheus-community.github.io/helm-charts \
  --version 29.36.1 --destination /opt/data/cache
python3 -m unittest scripts.tests.test_nfs_probe -v
python3 kubernetes/prometheus/tests/check.py \
  --upstream-chart /opt/data/cache/prometheus-29.36.1.tgz \
  --promtool /opt/data/cache/promtool
./scripts/check-storage-policy.sh
rumdl check kubernetes/prometheus/NFS-MONITORING.md
```

The check renders and lints both charts, verifies upstream rule loading and
scrape discovery, checks the embedded script, and runs seven PromQL scenarios
against the **rendered** rules. Unit tests exercise real scratch files, sample
validation, mount parsing, state transitions and HTTP with a simulated child
that remains blocked even after SIGKILL. They do not intentionally hang NFS.

## Integration checks after authorized GitOps rollout

The parent/operator owns commits and deployment. After both HelmReleases have
observed the committed revision, verify:

```sh
flux get helmrelease -n flux-system prometheus
flux get helmrelease -n flux-system prometheus-extras
kubectl -n prometheus get pvc nfs-probe-scratch
kubectl -n prometheus get ds nfs-worker-probe
kubectl -n prometheus get pods -l app.kubernetes.io/name=nfs-worker-probe -o wide
```

Expect one ready pod on each of node2 and node3, never on the control plane,
and a Bound scratch claim on `nfs-k8s`. In Prometheus, inspect `/api/v1/rules`
for both groups and `/api/v1/targets` for one `nfs-worker-probe` target per node.
Verify `nfs_probe_success == 1`, `nfs_probe_samples == 96`, advancing result
and success timestamps, and current TEST_STATEID rates near the healthy
baseline. Allow two complete batches before interpreting startup failures.
A successful exporter scrape alone does not prove healthy NFS. Confirm the
existing watchdog cron separately; distinguish configured routing from an
end-to-end failure delivery test.

Verified rollout on 2026-10-31: both HelmReleases reconciled successfully,
the scratch claim was Bound, and exactly one probe ran on node2 and node3.
Both targets were up, each returned 96 samples and success=1, and at least two
complete batches per worker were confirmed from Pod creation and success times.
Both TEST_STATEID rates were zero. All seven rules were healthy and inactive
once initial discovery completed. The watchdog's real observe-only call returned
healthy. Validation artifacts are under `/opt/data/reports` on the Hermes PVC.
