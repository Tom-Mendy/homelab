# NFS probe deadline starvation — 2026-11-03

## Incident and demonstrated cause

Repeated `node2: NFSProbeFailed` notifications alternated with recovery messages.
The notification means the synthetic batch failed; it does not itself establish
that the NAS restarted or that application data was inaccessible.

The original worker probes had a 100m CPU limit and a 20-second deadline for the
entire child process. Every child imported the exporter HTTP server stack before
validating its scratch mount or measuring file access. On node2, this cold-start
work was sufficiently CPU-starved to consume the deadline.

Evidence collected before correction:

- The live node2 probe's timeout counter was 450 at the first snapshot and
  increased during investigation; node3 had zero. Neither probe restarted.
- A sampled original child remained runnable (`R`, not uninterruptible `D`) while
  accumulating user CPU and minor faults, then became a SIGKILL zombie at the
  supervisor deadline. Its final CPU accounting was 156 user ticks plus 35 system
  ticks. The live sampling artifact is retained outside Git.
- On the same dedicated NFS scratch PVC, controlled 100m/500m comparisons used
  the same image, script, fixture algorithm and security context. Node2's script
  import phase took 9.498 seconds at 100m versus 1.034 seconds at 500m; these
  phase timings exclude the diagnostic wrapper's own bootstrap. The three NFS
  batch p95s were 0.636–2.093 ms at 100m and 0.611–0.781 ms at 500m.
- Both workers' current TEST_STATEID rates were zero. Node2's cumulative total
  was seven, unchanged in the host comparison window; zero rate does not mean
  zero lifetime count. Client RPC retransmissions were zero on both workers.
- NAS SSH inspection reported about twelve days of uptime, not repeated reboots
  during the alert period. The old node3 revoked-delegation storm is a different
  incident and does not justify repeating its reboot procedure.

Node2 has a much larger historical physical-interface RX-drop counter and an
older kernel than node3. Neither establishes this timeout's cause. No new RX drops
were observed in the bounded host comparison window. Worker SSH authentication
was unavailable, so kernel-log history was not established as clean. No keys,
NAS settings, node kernels or networking configuration were changed.

## Why messages alternated

The old watchdog considered only firing Prometheus rules after its client-counter
check. A failed probe could temporarily pass, clearing the rule; a subsequent
failure would start the rule's `for` timer again. The watchdog could announce
recovery after one observation with no firing alert, even while a new alert was
pending. The script's two-observation filter applied only to failure, not recovery.

## Durable correction

1. `http.server` is imported only by the long-lived exporter parent, not by each
   storage child. A subprocess regression test blocks that import in the actual
   child path and confirms invalid mounts still fail normally.
2. Probe CPU reservation is 50m and the burst limit is 500m, retaining the same
   image, 96-sample algorithm, memory limits, scratch PVC, non-root security,
   protocol and mount options. The child deadline remains **20 seconds** and all
   existing Prometheus alert thresholds remain unchanged.
3. The watchdog requires successful, fresh batches on both workers as well as
   absence of firing rules. Missing, stale and nonfinite input cannot declare
   recovery. Two consecutive healthy scheduler observations, five minutes apart,
   are now required before announcing recovery.
4. The scheduler wrapper executes an installed artifact at
   `/opt/data/scripts/homelab-nfs-watchdog-runtime.py`, with its SHA-256 verified
   against the versioned source. It no longer depends on a research worktree.
   Job `2773c05fe19e` remains active; its delivery route and frequency were not
   changed. No synthetic failure/recovery notification was sent to the user.

The probe correction is commit `198a08f`; the watchdog correction is `6bd7116`.
Probe manifests were deployed through Flux and read back after rollout. No
application PVC, production database or file contents were repaired or migrated.
Transient differential tests used only small per-UID fixtures on the existing
probe scratch claim; their Pods were removed. Their scratch directories follow
this claim's documented retained-fixture cleanup policy.

## Validation

- Regression tests were observed failing before the corresponding fixes, then
  passing. The complete `scripts/tests` suite passes: **17 tests**.
- Helm lint/render and strict kubeconform passed for the local extras chart;
  the storage policy check passed.
- The actual active upstream Prometheus chart **29.40.3** was linted and rendered;
  `promtool` checked seven rendered rules and passed seven rule scenarios. No
  alert threshold was relaxed to hide the symptom.
- Real watchdog observe-only evaluation returned `healthy: true`. No claim is
  made that this alone proves a new Matrix failure-message delivery test.

The bounded live verification completed successfully from **10:49:06 UTC to
11:01:06 UTC** on 2026-11-03: 25 observations across twelve minutes,
**13 distinct completed 96-sample batches per worker**, advancing success
timestamps, no blocked child and **zero new timeouts** on the same two post-rollout
Pods. Maximum observed synthetic batch p95 was **1.481 ms on node2** and
**0.557 ms on node3**. This is synthetic batch latency, not application-wide p95.

All pods were ready in the final cluster check, and no NFS rule was active. Final
NIC RX-drop and NFS RPC retransmission counters were unchanged from the independent
host comparison, so the historical drops did not recur in this observed window.
Raw samples remain in `/opt/data/reports/nfs-live-verification-20261103.json`.
The real scheduler ran the installed watchdog successfully; no artificial Matrix
alert was injected to demonstrate notification delivery.

## Evidence and limits

Restricted/local operational artifacts, not committed application data:

- `/opt/data/reports/nfs-cpu-ab-20261103.json`
- `/opt/data/reports/nfs-node2-live-child-20261103.log`
- `/opt/data/reports/nfs-investigation-hosts-20261103.md`
- `/opt/data/reports/nfs-live-verification-20261103.json`

This corrects demonstrated monitoring/runtime defects, not all possible causes
of future NFS outages. A bounded successful observation is not a guarantee against
hardware, network or NAS failure. Genuine blocked-child, stale-result and failed
storage tests remain alertable. Prometheus and Hermes depend on this NAS, so a
total NAS outage still needs an independent external monitoring path.
