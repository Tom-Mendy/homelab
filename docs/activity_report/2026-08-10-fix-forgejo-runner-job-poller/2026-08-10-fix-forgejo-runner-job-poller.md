# Fix the Forgejo runner job poller

## Problem

The Forgejo runner pod was `2/2 Running`, registered with the expected
`debian` and `ubuntu-latest` labels, and continuously heartbeating. New Actions
jobs nevertheless remained waiting with no task assignment.

## Investigation and reasoning

The runner could reach Forgejo successfully:

```text
forgejo-runner version v12.12.0
GET http://forgejo.forgejo.svc.cluster.local:3000/api/healthz
HTTP/1.1 200 OK
```

The read-only Forgejo database query showed the mismatch:

```text
runner: forgejo-runner-homelab
labels: ["debian","ubuntu-latest"]
last_online: current
last_active: previous job

job 101  validate  ["ubuntu-latest"]  task_id=0  waiting
job 102  publish   ["ubuntu-latest"]  task_id=0  waiting
```

This matched the previously observed long-lived daemon poller stall. The old
`one-job --wait` workaround refreshed the poller but made the Deployment enter
`CrashLoopBackOff` after each successful one-shot process exit.

## Commands and results

The live Deployment was restarted to clear the stalled daemon:

```text
kubectl -n forgejo-runner rollout restart deployment/forgejo-runner-homelab
deployment "forgejo-runner-homelab" successfully rolled out
```

The waiting job was assigned immediately:

```text
job 101  validate  task_id=24  status=6
task 24 repo is Tom-Mendy/homelab
```

## Change and final outcome

The runner now executes `one-job --wait` in a loop inside the same container.
A successful job starts a fresh poller immediately. A polling error waits five
seconds before retrying. The pod and Docker sidecar remain alive, avoiding the
former CrashLoop behavior.

Validation results:

```text
helm template forgejo-runner kubernetes/forgejo-runner
rendered one-job loop successfully

./scripts/test-helm-chart.sh
all 23 charts: OK

./scripts/check-storage-policy.sh
storage policy ok
```
