# Fix SearXNG CrashLoopBackOff

## Problem

The `searxng` pod had one healthy `gluetun` sidecar and one crashing
`searxng` container:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n searxng get pods,deploy,svc,pvc -o wide
```

Observed state before the fix:

```text
NAME                           READY   STATUS             RESTARTS   NODE
pod/searxng-5b6b574d8f-486d5   1/2     CrashLoopBackOff   1251       node2

NAME                      READY   UP-TO-DATE   AVAILABLE
deployment.apps/searxng   0/1     1            0

NAME              TYPE        CLUSTER-IP    PORT(S)
service/searxng   ClusterIP   10.233.45.2   8080/TCP
```

## Reasoning path

Check container status:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n searxng get pod searxng-5b6b574d8f-486d5 \
  -o jsonpath='{.status.containerStatuses[*].name}{"\n"}...'
```

First attempt failed from sandbox networking:

```text
Unable to connect to the server: dial tcp 192.168.1.11:6443:
socket: operation not permitted
```

After allowing cluster access, the same command showed:

```text
gluetun searxng
gluetun state: running
searxng state: waiting, reason CrashLoopBackOff
searxng last state: terminated, exitCode 2, reason Error
```

Check previous container logs:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n searxng logs pod/searxng-5b6b574d8f-486d5 \
  -c searxng --previous --tail=160
```

The logs showed the real failure:

```text
SearXNG 2026.5.10-df1f24fb7
...
Usage: granian [OPTIONS] APP
Try 'granian --help' for help.

Error: Invalid value for '--port': 'tcp://10.233.45.2:8080'
is not a valid integer.
```

Kubernetes injects service environment variables into pods by default. Because
the service is also named `searxng`, Kubernetes injected
`SEARXNG_PORT=tcp://10.233.45.2:8080`. The newer SearXNG image passed that value
to `granian --port`, which expects an integer.

## Commands and results

Patch the live deployment to disable service environment variable injection:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n searxng patch deploy searxng \
  --type merge \
  -p '{"spec":{"template":{"spec":{"enableServiceLinks":false}}}}'
```

Result:

```text
deployment.apps/searxng patched
```

Wait for rollout:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n searxng rollout status deploy/searxng --timeout=180s
```

Result:

```text
Waiting for deployment "searxng" rollout to finish:
1 old replicas are pending termination...
Waiting for deployment "searxng" rollout to finish:
1 old replicas are pending termination...
Waiting for deployment "searxng" rollout to finish:
1 old replicas are pending termination...
deployment "searxng" successfully rolled out
```

Verify Kubernetes state:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n searxng get pods,deploy,svc,pvc -o wide
```

Result:

```text
NAME                          READY   STATUS    RESTARTS   NODE
pod/searxng-c987bf4b5-72m5k   2/2     Running   0          node3

NAME                      READY   UP-TO-DATE   AVAILABLE
deployment.apps/searxng   1/1     1            1

NAME              TYPE        CLUSTER-IP    PORT(S)
service/searxng   ClusterIP   10.233.45.2   8080/TCP
```

Check fixed container logs:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n searxng logs deploy/searxng -c searxng --tail=80
```

Relevant result:

```text
SearXNG 2026.2.16-8e824017d
...
[INFO] Starting granian (main PID: 1)
[INFO] Listening at: http://:::8080
[INFO] Spawning worker-1 with PID: 925
[INFO] Started worker-1
```

Some search engine initialization warnings remained, but the application process
started and stayed running.

Check repository storage policy:

```sh
./scripts/check-storage-policy.sh
```

Result:

```text
storage policy ok
```

## Final outcome

SearXNG recovered. The deployment is available, and the new pod is `2/2`
`Running`.

The GitOps chart was updated so Argo CD keeps the same setting:

```yaml
spec:
  template:
    spec:
      enableServiceLinks: false
```

No persistent storage was added or changed. No `local-path` usage was added.
