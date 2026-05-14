# OpenWebUI PVC migration to nfs-k8s

## 1. Problem to solve

OpenWebUI still used a worker-local `local-path` PVC:

```text
openwebui/openwebui-open-webui   Bound   local-path
```

That meant the OpenWebUI data was tied to one worker node. If that node went
down, Kubernetes could not safely reschedule the workload with its data.

## 2. Reasoning path and commands

First, inspect the application and PVC:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n openwebui get deploy,statefulset,pod,pvc -o wide
```

Useful result:

```text
statefulset.apps/openwebui-open-webui   1/1
pod/openwebui-open-webui-0              1/1   Running   node2
persistentvolumeclaim/openwebui-open-webui   Bound   local-path
```

Then inspect the Argo CD app state:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n argocd get app openwebui \
  -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,AUTO:.spec.syncPolicy.automated
```

Result:

```text
openwebui   Synced   Healthy   map[prune:true selfHeal:true]
```

Because the PVC `storageClassName` is immutable, the migration could not be done
by only changing Git and letting Argo CD sync. The data had to be copied, the old
PVC deleted, and a new PVC with the same name created using `nfs-k8s`.

Suspend OpenWebUI auto-sync during the migration:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n argocd patch app openwebui \
  --type=merge \
  -p='{"spec":{"syncPolicy":{"automated":null}}}'
```

Create a temporary NFS PVC:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: openwebui-nfs-migration
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs-k8s
  resources:
    requests:
      storage: 50Gi
```

Wait until it is bound:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n openwebui wait \
  --for=jsonpath='{.status.phase}'=Bound \
  pvc/openwebui-nfs-migration \
  --timeout=60s
```

Stop the StatefulSet before copying SQLite data:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n openwebui scale statefulset/openwebui-open-webui --replicas=0

kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n openwebui wait --for=delete pod/openwebui-open-webui-0 --timeout=120s
```

Copy from the old PVC to the temporary NFS PVC using a temporary pod:

```bash
du -sh /old
cd /old
tar cpf - . | tar xpf - -C /new
du -sh /new
find /new -maxdepth 2 -type f -print | sort | head -80
```

## 3. Results, including failed or useful intermediate commands

The initial copy completed successfully:

```text
1.1G    /old
930M    /new
/new/uploads/cf2bf9a7-442d-450e-a8fa-e75f9cc75e73_f75b8fc0-1136-457a-a8e0-c390f8d7d0b1.pdf
/new/vector_db/chroma.sqlite3
/new/webui.db
/new/webui.db-shm
/new/webui.db-wal
```

The size changed slightly because filesystem accounting differs between the old
local path volume and the NFS volume, but the expected OpenWebUI files were
present.

Then delete the old PVC:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n openwebui delete pvc openwebui-open-webui
```

Recreate the final PVC with the original name and `nfs-k8s`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: openwebui-open-webui
  annotations:
    argocd.argoproj.io/tracking-id: openwebui:/PersistentVolumeClaim:openwebui/openwebui-open-webui
  labels:
    app.kubernetes.io/component: open-webui
    app.kubernetes.io/instance: openwebui
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: nfs-k8s
  resources:
    requests:
      storage: 50Gi
```

Final copy from temporary NFS PVC to final NFS PVC:

```text
1.1G    /src
1.1G    /dst
/dst/uploads/cf2bf9a7-442d-450e-a8fa-e75f9cc75e73_f75b8fc0-1136-457a-a8e0-c390f8d7d0b1.pdf
/dst/vector_db/chroma.sqlite3
/dst/webui.db
/dst/webui.db-shm
/dst/webui.db-wal
```

Start OpenWebUI again:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n openwebui scale statefulset/openwebui-open-webui --replicas=1

kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n openwebui rollout status statefulset/openwebui-open-webui --timeout=240s
```

Result:

```text
partitioned roll out complete: 1 new pods have been updated...
```

Verify pod and PVC:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n openwebui get pod,pvc -o wide
```

Result:

```text
pod/openwebui-open-webui-0      1/1   Running
openwebui-open-webui            Bound   nfs-k8s
```

Logs showed OpenWebUI started correctly:

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
v0.9.5 - building the best AI user interface.
INFO:     Started server process
```

Temporary cleanup:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n openwebui delete pvc openwebui-nfs-migration

kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  delete pv pvc-0db47996-ba66-4193-8f12-1a2bd6c06930
```

Because `nfs-k8s` uses `Retain`, the temporary NFS directory also had to be
removed through a cleanup pod mounting `/volume1/k8s`.

## 4. Final outcome and required changes

OpenWebUI now runs with its main PVC on `nfs-k8s`:

```text
openwebui/openwebui-open-webui   Bound   nfs-k8s
```

The GitOps values were changed from:

```yaml
persistence:
  storageClass: "local-path"
pipelines:
  persistence:
    storageClass: local-path
```

to:

```yaml
persistence:
  storageClass: nfs-k8s
pipelines:
  persistence:
    storageClass: nfs-k8s
```

The OpenWebUI values file was removed from
`scripts/storage-policy-local-path-allowlist.txt`.

The final necessary change is to commit and push the updated GitOps manifests so
Argo CD keeps OpenWebUI on `nfs-k8s` instead of trying to return to the old
`local-path` desired state.
