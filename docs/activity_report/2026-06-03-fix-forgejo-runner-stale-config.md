# Fix Forgejo Runner Stale Config

## Problem

After Forgejo moved to the canonical URL `https://forgejo.tom-mendy.com/`, the
Forgejo Actions runner appeared online but stopped taking new jobs.

The current queued job had no runner task assigned:

```text
id  run_id  name      runs_on            task_id  status
--  ------  --------  -----------------  -------  ------
42  42      validate  ["ubuntu-latest"]  0        5
```

## Reasoning Path

Check live runner and Forgejo pods:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config get pods -n forgejo-runner -o wide
kubectl --kubeconfig /home/tmendy/.kube/config get pods -n forgejo -o wide
```

Result:

```text
forgejo-runner-homelab-645bfdf494-t8hhs   2/2   Running   11d
forgejo-f8df4888c-hndgv                   1/1   Running   11d
```

Inspect runner logs:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config logs \
  -n forgejo-runner deploy/forgejo-runner-homelab -c runner --tail=160
```

Relevant output:

```text
runner: forgejo-runner-homelab, with version: v12.10.1, with labels:
[ubuntu-latest], ephemeral: false, declared successfully
failed to fetch task: deadline exceeded; increase fetch_timeout if this error
is persistent
```

Check the live ConfigMap and the config actually copied into `/data/config.yaml`:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config get cm \
  -n forgejo-runner forgejo-runner-config -o yaml
kubectl --kubeconfig /home/tmendy/.kube/config exec \
  -n forgejo-runner deploy/forgejo-runner-homelab -c runner -- \
  sed -n '1,160p' /data/config.yaml
```

The ConfigMap had both labels:

```text
["debian","ubuntu-latest"]
```

The running pod still had the old copied config:

```text
labels:
  - "ubuntu-latest:docker://node:20-bookworm"
```

This showed that the ConfigMap had changed, but the pod had not restarted, so
the runner kept stale runtime config.

Check Forgejo DB state without reading runner tokens:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config exec -n forgejo deploy/forgejo \
  -- sh -c 'sqlite3 -header -column /data/gitea/gitea.db \
  "select id,run_id,name,runs_on,task_id,status from action_run_job \
  order by id desc limit 5;"'
```

The recent jobs had `task_id=0`, while `action_task` only contained the two old
tasks from 2026-05-22.

## Command Results

Restart the runner deployment to reload the ConfigMap and reconnect polling:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config rollout restart \
  deployment/forgejo-runner-homelab -n forgejo-runner
kubectl --kubeconfig /home/tmendy/.kube/config rollout status \
  deployment/forgejo-runner-homelab -n forgejo-runner --timeout=120s
```

Result:

```text
deployment.apps/forgejo-runner-homelab restarted
deployment "forgejo-runner-homelab" successfully rolled out
```

The first runner start failed because Docker-in-Docker was not ready yet:

```text
Error: cannot ping the docker daemon. is it running? Cannot connect to the Docker
daemon at tcp://127.0.0.1:2375. Is the docker daemon running?
```

After container restart, the runner became ready and declared both labels:

```text
runner: forgejo-runner-homelab, with version: v12.10.1, with labels:
[debian ubuntu-latest], ephemeral: false, declared successfully
[poller] launched
task 3 repo is Tom-Mendy/homelab https://data.forgejo.org
http://forgejo.forgejo.svc.cluster.local:3000/
```

Forgejo DB then showed the queued job had been assigned:

```text
id  run_id  name      task_id  status
--  ------  --------  -------  ------
42  42      validate  3        6
```

The run then finished with start/stop timestamps and no pre-execution error:

```text
id  status  started              stopped
--  ------  -------------------  -------------------
42  2       2026-06-03 07:57:24  2026-06-03 08:00:05
```

## Final Outcome

The live runner now takes jobs again.

The chart was also changed so this does not recur:

- Add a `checksum/runner-config` pod template annotation so ConfigMap changes
  roll the Deployment.
- Add `sleep 5` before `forgejo-runner daemon` so Docker-in-Docker has time to
  start before the runner checks Docker.

No persistent storage changed, and no `local-path` storage was added.
