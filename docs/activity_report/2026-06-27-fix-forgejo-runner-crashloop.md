# Fix Forgejo Runner CrashLoop

## Problem

After the VPN pods recovered, `forgejo-runner-homelab` appeared in
`CrashLoopBackOff`:

```text
forgejo-runner forgejo-runner-homelab-7c48cdbb45-d645h 1/2 CrashLoopBackOff
```

## Reasoning and Commands

Check container status:

```sh
kubectl get pod -n forgejo-runner forgejo-runner-homelab-7c48cdbb45-d645h -o json |
  jq -r '.status.containerStatuses[] |
    [.name,.ready,.state.waiting.reason // .state.running.startedAt // .state.terminated.reason,
     .lastState.terminated.reason,.lastState.terminated.exitCode,.restartCount] | @tsv'
```

Result:

```text
docker  true   2026-06-16T03:50:49Z
runner  false  CrashLoopBackOff  Completed  0  7
```

The runner container was exiting with code `0`, so it was not crashing from an
application error. The Deployment command was:

```sh
forgejo-runner --config /data/config.yaml one-job --wait
```

Previous runner logs showed the process completed exactly one task and then
shut down:

```sh
kubectl logs -n forgejo-runner forgejo-runner-homelab-7c48cdbb45-d645h -c runner --previous --tail=120
```

Useful result:

```text
single task poller successfully fetched one task
single task poller is shutting down
```

That behavior is valid for a one-shot command, but not for a Kubernetes
Deployment with `restartPolicy: Always`; the normal exit causes repeated
restarts and eventually `CrashLoopBackOff`.

## Changes

Changed the runner command back to daemon mode:

```sh
forgejo-runner --config /data/config.yaml daemon
```

Updated:

```text
kubernetes/forgejo-runner/templates/deployment.yaml
kubernetes/forgejo-runner/README.md
```

## Verification

Storage policy:

```sh
./scripts/check-storage-policy.sh
```

Rollout:

```sh
kubectl rollout status -n forgejo-runner deploy/forgejo-runner-homelab --timeout=180s
```

Final CrashLoopBackOff scan:

```sh
kubectl get pods -A | rg 'CrashLoopBackOff|Init:CrashLoopBackOff|Error|Terminating' || true
```

## Outcome

The Forgejo runner is again a long-lived Deployment workload. This removes the
false CrashLoopBackOff caused by normal `one-job` completion.
