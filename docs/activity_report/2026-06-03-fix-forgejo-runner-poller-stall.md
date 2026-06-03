# Fix Forgejo Runner Poller Stall

## Problem

Forgejo Actions showed the `homelab-validation.yml` job waiting for a runner
with label `ubuntu-latest`.

The live runner pod was running and registered both expected labels:

```text
runner: forgejo-runner-homelab, with version: v12.10.1, with labels:
[debian ubuntu-latest], ephemeral: false, declared successfully
```

The newest job was still queued with no task assignment:

```text
id  run_id  name      runs_on            task_id  status
--  ------  --------  -----------------  -------  ------
45  45      validate  ["ubuntu-latest"]  0        5
```

The previous task had finished, but the long-lived runner daemon did not pick up
the next queued job.

## Reasoning Path

Check live runner pod:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config \
  get pods -n forgejo-runner -o wide
```

Result:

```text
forgejo-runner-homelab-6b55c-b4grn  2/2  Running  0  23m  node2
```

Check live runner logs:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config logs \
  -n forgejo-runner deploy/forgejo-runner-homelab -c runner --tail=120
```

Relevant output:

```text
runner: forgejo-runner-homelab, with version: v12.10.1, with labels:
[debian ubuntu-latest], ephemeral: false, declared successfully
[poller] launched
task 4 repo is Tom-Mendy/homelab https://data.forgejo.org
http://forgejo.forgejo.svc.cluster.local:3000/
```

Check Forgejo Actions job table:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config exec -n forgejo deploy/forgejo \
  -- sh -c 'sqlite3 -header -column /data/gitea/gitea.db \
  "select id,run_id,name,runs_on,task_id,status,started,stopped
   from action_run_job order by id desc limit 10;"'
```

Result showed the latest job had no task:

```text
45  45  validate  ["ubuntu-latest"]  0  5  0  0
43  43  validate  ["ubuntu-latest"]  4  2  1780473971  1780474140
```

Check runner task table:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config exec -n forgejo deploy/forgejo \
  -- sh -c 'sqlite3 -header -column /data/gitea/gitea.db \
  "select id,job_id,runner_id,status,started,stopped
   from action_task order by id desc limit 10;"'
```

Result:

```text
4  43  1  2  1780473971  1780474140
3  42  1  2  1780473444  1780473605
```

The runner process was alive and heartbeating, but no new task was created for
job 45. This pointed to the long-lived daemon poller being stuck after
completing task 4.

Inspect runner CLI options:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config exec \
  -n forgejo-runner deploy/forgejo-runner-homelab -c runner -- \
  forgejo-runner one-job --help
```

Relevant output:

```text
Run only one job
--wait  waits until task has been assigned
```

## Command Results

Restart the live runner deployment to unblock the queued job:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config rollout restart \
  deployment/forgejo-runner-homelab -n forgejo-runner
kubectl --kubeconfig /home/tmendy/.kube/config rollout status \
  deployment/forgejo-runner-homelab -n forgejo-runner --timeout=180s
```

Result:

```text
deployment.apps/forgejo-runner-homelab restarted
deployment "forgejo-runner-homelab" successfully rolled out
```

After restart, job 45 was assigned:

```text
id  run_id  name      runs_on            task_id  status  started     stopped
--  ------  --------  -----------------  -------  ------  ----------  -------
45  45      validate  ["ubuntu-latest"]  5        6       1780475590  0
```

The chart was changed so the runner process uses one-job mode:

```sh
forgejo-runner --config /data/config.yaml one-job --wait
```

After each job, the runner container exits and Kubernetes restarts it. This
keeps the polling loop fresh for the next queued job while keeping the Docker
sidecar and pod-level config.

## Verification

Render the Forgejo runner chart:

```sh
helm template test kubernetes/forgejo-runner
```

Rendered command:

```text
forgejo-runner --config /data/config.yaml one-job --wait
```

Run all local chart checks:

```sh
./scripts/test-helm-chart.sh
```

```text
=== atuin ===
OK
...
=== vaultwarden ===
OK
```

Storage policy check:

```sh
./scripts/check-storage-policy.sh
```

```text
storage policy ok
```

Local kubeconform check:

```sh
./scripts/kubeconform-local-charts.sh
```

```text
kubeconform is required but was not found in PATH
```

This local environment does not have `kubeconform` installed.

Markdown check for updated runner docs:

```sh
rumdl check --fix kubernetes/forgejo-runner/README.md
```

```text
Success: No issues found in 1 file
```

## Final Outcome

The live queued Forgejo job was assigned after runner restart.

The repository now configures the Forgejo runner to process one job per runner
container lifetime. This avoids a stale daemon poller leaving future jobs stuck
at `Waiting for a runner with the following label: ubuntu-latest`.

No persistent storage changed, and no `local-path` storage was added.
