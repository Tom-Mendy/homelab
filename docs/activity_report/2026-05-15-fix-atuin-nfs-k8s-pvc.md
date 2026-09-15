# 2026-05-15 Fix Atuin PVCs on nfs-k8s

<!-- markdownlint-disable MD013 -->

## Problem

Atuin and its Postgres database were stuck in `CrashLoopBackOff`:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin get pods,deploy,svc,pvc -o wide
```

```text
NAME                           READY   STATUS             RESTARTS           AGE     IP             NODE
pod/atuin-c9645898b-wjmkr      0/1     CrashLoopBackOff   1254 (3m53s ago)   4d10h   10.233.75.20   node2
pod/postgres-bb6f5dd95-9gprw   0/1     CrashLoopBackOff   1254 (30s ago)     4d10h   10.233.75.26   node2

NAME                                     STATUS   VOLUME                      CAPACITY   ACCESS MODES   STORAGECLASS
persistentvolumeclaim/atuin-config-v2    Bound    atuin-data-pv-v2            20Gi       RWX
persistentvolumeclaim/postgres-data-v2   Bound    atuin-postgres-data-pv-v2   10Gi       RWO
```

The PVCs were backed by static NFS PVs with an empty storage class, not the
standard dynamic `nfs-k8s` class.

## Reasoning path

The first attempt used the user's shell alias:

```sh
k -n atuin describe pod -l app=postgres
```

```text
zsh:1: command not found: k
```

The next attempt used the full kubeconfig command, but the local sandbox blocked
cluster network access:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin logs deploy/postgres --tail=120
```

```text
Unable to connect to the server: dial tcp 192.168.1.11:6443: socket: operation not permitted
```

After approving cluster access, the container logs showed two independent
storage problems.

Postgres failed because the mount root was non-empty:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin logs deploy/postgres --tail=120
```

```text
initdb: error: directory "/var/lib/postgresql/data" exists but is not empty
initdb: hint: If you want to create a new database system, either remove or empty the directory "/var/lib/postgresql/data" or run initdb with an argument other than "/var/lib/postgresql/data".
```

Atuin failed because it could not write its config file:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin logs deploy/atuin --tail=120
```

```text
Error: could not load server settings

Caused by:
    failed to create file `/config/server.toml`: Permission denied (os error 13)
```

Inspecting the chart showed that Atuin used static NFS PVs:

```sh
rg -n "atuin|postgres|storageClassName" kubernetes/atuin -S
```

The relevant values were:

```yaml
storageClassName: ""
nfsServer: 192.168.1.1
nfsPath: /volume1/atuin
```

The fix was to use dynamic `nfs-k8s` PVCs and set Postgres `PGDATA` to a
subdirectory so `initdb` does not reject the mount root.

## Commands and results

The chart was changed so both PVCs use `storageClassName: nfs-k8s`, static PVs
are only rendered when explicit static NFS fields are set, and Postgres uses:

```yaml
- name: PGDATA
  value: /var/lib/postgresql/data/pgdata
```

The rendered manifests were checked:

```sh
helm template atuin kubernetes/atuin
```

```text
kind: PersistentVolumeClaim
metadata:
  name: postgres-data-v2
spec:
  storageClassName: "nfs-k8s"
---
kind: PersistentVolumeClaim
metadata:
  name: atuin-config-v2
spec:
  storageClassName: "nfs-k8s"
```

The repository storage policy passed:

```sh
./scripts/check-storage-policy.sh
```

```text
storage policy ok
```

Argo CD restored the `argocd/atuin` sync policy when only the Atuin app was
paused. The parent app was identified as `argocd/homelab`, so both apps were
temporarily paused:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n argocd patch application homelab --type=json -p='[{"op":"remove","path":"/spec/syncPolicy"}]'
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n argocd patch application atuin --type=json -p='[{"op":"remove","path":"/spec/syncPolicy"}]'
```

```text
application.argoproj.io/homelab patched
application.argoproj.io/atuin patched
```

The workloads were stopped:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin scale deploy/atuin deploy/postgres --replicas=0
```

```text
deployment.apps/atuin scaled
deployment.apps/postgres scaled
```

The old Kubernetes PVC objects were deleted. This did not delete the Synology
NFS directories.

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin delete pvc atuin-config-v2 postgres-data-v2
```

```text
persistentvolumeclaim "atuin-config-v2" deleted
persistentvolumeclaim "postgres-data-v2" deleted
```

The old static PV objects moved to `Released` and were deleted. Their reclaim
policy was `Retain`.

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" get pv atuin-data-pv-v2 atuin-postgres-data-pv-v2
```

```text
NAME                        CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS     CLAIM                    STORAGECLASS
atuin-data-pv-v2            20Gi       RWX            Retain           Released   atuin/atuin-config-v2
atuin-postgres-data-pv-v2   10Gi       RWO            Retain           Released   atuin/postgres-data-v2
```

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" delete pv atuin-data-pv-v2 atuin-postgres-data-pv-v2
```

```text
persistentvolume "atuin-data-pv-v2" deleted
persistentvolume "atuin-postgres-data-pv-v2" deleted
```

The fixed chart output was applied:

```sh
helm template atuin kubernetes/atuin --output-dir /tmp/atuin-rendered
kubectl --kubeconfig "$HOME/.kube/config-homelab" apply -f /tmp/atuin-rendered/atuin-local/templates
```

```text
deployment.apps/atuin configured
service/atuin configured
ingress.networking.k8s.io/atuin-ingress configured
namespace/atuin configured
deployment.apps/postgres configured
service/postgres configured
persistentvolumeclaim/postgres-data-v2 created
persistentvolumeclaim/atuin-config-v2 created
secret/atuin-secrets configured
```

Both deployments rolled out:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin rollout status deploy/postgres --timeout=180s
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin rollout status deploy/atuin --timeout=180s
```

```text
deployment "postgres" successfully rolled out
deployment "atuin" successfully rolled out
```

Postgres initialized successfully:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin logs deploy/postgres --tail=80
```

```text
fixing permissions on existing directory /var/lib/postgresql/data/pgdata ... ok
creating subdirectories ... ok
running bootstrap script ... ok
syncing data to disk ... ok
Success. You can now start the database server using:
    pg_ctl -D /var/lib/postgresql/data/pgdata -l logfile start
PostgreSQL init process complete; ready for start up.
2026-05-15 06:24:08.655 UTC [1] LOG:  database system is ready to accept connections
```

The Atuin log was empty after startup, and the deployment was ready.

## Final outcome

Atuin and Postgres are running:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin get pods,deploy,pvc -o wide
```

```text
NAME                           READY   STATUS    RESTARTS   AGE   IP             NODE
pod/atuin-c9645898b-zl26n      1/1     Running   0          21s   10.233.71.33   node3
pod/postgres-7b68b458f-2gqzv   1/1     Running   0          18s   10.233.71.34   node3

NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/atuin      1/1     1            1           57d
deployment.apps/postgres   1/1     1            1           57d

NAME                                     STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
persistentvolumeclaim/atuin-config-v2    Bound    pvc-717898a7-6a05-4e19-91d7-34dbb26be28f   20Gi       RWX            nfs-k8s
persistentvolumeclaim/postgres-data-v2   Bound    pvc-a6b539a0-fd00-4f21-af94-33bbd1edc006   10Gi       RWO            nfs-k8s
```

The new PVs are dynamic `nfs-k8s` volumes:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" get pv pvc-717898a7-6a05-4e19-91d7-34dbb26be28f pvc-a6b539a0-fd00-4f21-af94-33bbd1edc006 -o wide
```

```text
NAME                                       CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                    STORAGECLASS
pvc-717898a7-6a05-4e19-91d7-34dbb26be28f   20Gi       RWX            Retain           Bound    atuin/atuin-config-v2    nfs-k8s
pvc-a6b539a0-fd00-4f21-af94-33bbd1edc006   10Gi       RWO            Retain           Bound    atuin/postgres-data-v2   nfs-k8s
```

`argocd/homelab` and `argocd/atuin` auto-sync remain paused until the repository
fix is pushed to the Forgejo GitOps source. Re-enable them only after Forgejo has
the fixed chart, or Argo CD will revert the live repair back to the old static
PV manifests.
