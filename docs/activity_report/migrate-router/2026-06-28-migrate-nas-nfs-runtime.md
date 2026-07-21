# Migrate NAS NFS Runtime Access

## Problem

The Synology NAS now responds on the new LAN IP `10.0.0.11`, but live
Kubernetes PV objects still reference the old NFS server IP `192.168.1.1`.

The PV field `spec.nfs.server` cannot be patched in place, so cutting the old
IP immediately would break future remounts for existing volumes.

## Reasoning and Commands

The NAS export was checked on the new IP:

```sh
showmount -e 10.0.0.11
```

Observed result:

```text
/volume1/Downloads   10.0.0.0/24,192.168.1.0/24
/volume1/music       10.0.0.0/24,192.168.1.0/24
/volume1/prometheus  10.0.0.0/24,192.168.1.0/24
/volume1/video       10.0.0.0/24,192.168.1.0/24
/volume1/vaultwarden 10.0.0.0/24,192.168.1.0/24
/volume1/forgejo     10.0.0.0/24,192.168.1.0/24
/volume1/k8s         10.0.0.0/24,192.168.1.0/24
```

Live PVs were listed:

```sh
kubectl --tls-server-name=node1 get pv \
  -o jsonpath='{range .items[?(@.spec.nfs.server)]}{.metadata.name}{"\t"}{.spec.nfs.server}{"\t"}{.spec.nfs.path}{"\t"}{.spec.claimRef.namespace}{"/"}{.spec.claimRef.name}{"\n"}{end}'
```

All existing NFS PVs initially still pointed to `192.168.1.1`.

As a temporary compatibility layer, node-local NAT was added on `node1`,
`node2`, and `node3`:

```sh
sudo iptables -t nat -A OUTPUT \
  -d 192.168.1.1/32 \
  -j DNAT --to-destination 10.0.0.11
```

## Results

The compatibility rule is active on all three Kubernetes nodes:

```text
-A OUTPUT -d 192.168.1.1/32 -j DNAT --to-destination 10.0.0.11
```

After the rule, `showmount -e 192.168.1.1` works from those nodes because the
traffic is redirected to `10.0.0.11`.

No pods were stuck after the NAS move:

```text
No resources found
```

The PV/PVC migration required live deletion and recreation because
`spec.nfs.server` is immutable on a Bound PV. A JSON backup and generated PV/PVC
objects were written under:

```text
/tmp/homelab-pv-nfs-migration/
```

The migration was done in batches:

1. Static media and application PVs.
2. Dynamic application PVCs.
3. Database and Redis PVCs.
4. The NFS provisioner backing PV.

After recreating the PV/PVC objects, all NFS PVs referenced `10.0.0.11`:

```text
forgejo-data-pv                                      Bound  10.0.0.11
media-downloads-pv                                   Bound  10.0.0.11
media-movies-pv                                      Bound  10.0.0.11
media-series-pv                                      Bound  10.0.0.11
navidrome-music-pv                                   Bound  10.0.0.11
prometheus-server-pv                                 Bound  10.0.0.11
pv-nfs-provisioner-nfs-subdir-external-provisioner   Bound  10.0.0.11
vaultwarden-data-pv                                  Bound  10.0.0.11
```

The remaining dynamically provisioned PVs also showed `10.0.0.11`.

PVC health was checked:

```sh
kubectl --tls-server-name=node1 get pvc -A | rg 'Lost|Pending|Terminating|NAME'
```

Observed result:

```text
No Lost, Pending, or Terminating PVCs were returned.
```

Workload health was checked:

```sh
kubectl --tls-server-name=node1 get pods -A \
  --field-selector=status.phase!=Running,status.phase!=Succeeded -o wide
```

Observed result:

```text
No resources found
```

The storage policy check passed:

```sh
./scripts/check-storage-policy.sh
```

Observed result:

```text
storage policy ok
```

Pods using NFS were then deleted so their controllers would recreate them and
remount volumes from the updated PV objects.

The static NFS mounts came back on `10.0.0.11`, but `findmnt` on `node3` still
showed some dynamic `nfs-k8s` mounts with the old displayed source
`192.168.1.1`. Because of that, the temporary DNAT rule must remain in place
until kubelet refreshes and those mounts are recreated from `10.0.0.11`.

The next step was to restart kubelet on `node3` and delete only pods whose live
mounts still referenced `192.168.1.1`:

<!-- rumdl-disable MD013 -->

```sh
ssh 10.0.0.23 'sudo systemctl restart kubelet'

for uid in $(
  for h in 10.0.0.21 10.0.0.22 10.0.0.23; do
    ssh "$h" "findmnt -t nfs,nfs4 -n -o SOURCE,TARGET \
      | awk '\$1 ~ /^192\\.168\\.1\\.1:/ {print \$2}' \
      | sed -n 's#.*pods/\\([^/]*\\)/.*#\\1#p'"
  done | sort -u
); do
  kubectl --tls-server-name=node1 get pods -A -o json \
    | jq -r --arg uid "$uid" '.items[] | select(.metadata.uid == $uid) | "\(.metadata.namespace) \(.metadata.name)"'
done | while read -r ns pod; do
  kubectl --tls-server-name=node1 -n "$ns" delete pod "$pod" --wait=false
done
```

<!-- rumdl-enable MD013 -->

Observed result:

<!-- rumdl-disable MD013 -->

```text
pod "atuin-7b754fbc8c-9rvfl" deleted from atuin namespace
pod "bazarr-554ff7d779-zvvdz" deleted from media namespace
pod "nzbget-76d5d9fc9-6w9n9" deleted from media namespace
pod "autobrr-78b7f7989f-2xmv5" deleted from media namespace
pod "sonarr-5b7f7d8fd4-79h8p" deleted from media namespace
pod "navidrome-9bc897fc9-xcxr4" deleted from navidrome namespace
pod "nfs-provisioner-nfs-subdir-external-provisioner-7cb846968cmwgdb" deleted from nfs-provisioner namespace
pod "redis-master-0" deleted from infisical namespace
pod "radarr-86d464fdcd-bxn7s" deleted from media namespace
pod "prowlarr-754f8d444c-8272c" deleted from media namespace
pod "grafana-646c84fffd-wxqb7" deleted from grafana namespace
pod "ollama-7df7b6f5d-9hwxz" deleted from ollama namespace
pod "authentik-postgres-1" deleted from authentik namespace
pod "traefik-6c9cc6d9d9-xp4m7" deleted from traefik namespace
pod "open-webui-0" deleted from openwebui namespace
pod "qbittorrent-5595d5b976-x2fgz" deleted from media namespace
pod "infisical-postgres-1" deleted from infisical namespace
pod "postgres-7b68b458f-phv48" deleted from atuin namespace
```

<!-- rumdl-enable MD013 -->

The replacement pods initially came back healthy, but `node3` reused stale NFS
mounts. The live API was checked to make sure the source of truth was correct:

```sh
kubectl --tls-server-name=node1 get pv -o json \
  | jq -r '.items[] | select(.spec.nfs.server == "192.168.1.1") | .metadata.name'
```

Observed result:

```text
No PVs were returned.
```

The NFS provisioner deployment was also checked and already used `10.0.0.11`:

```text
NFS_SERVER=10.0.0.11
NFS_PATH=/volume1/k8s
```

Because the remaining issue was local to `node3`, the node was cordoned and the
same stale-mounted pods were deleted again so the node could release the old
mounts:

```sh
kubectl --tls-server-name=node1 cordon node3
```

Observed result:

```text
node/node3 cordoned
```

Most replacement pods moved away from `node3`. `ollama` stayed Pending while
`node3` was cordoned, which was expected for this cleanup window:

<!-- rumdl-disable MD013 -->

```text
NAMESPACE   NAME                     READY   STATUS    RESTARTS   AGE     IP       NODE     NOMINATED NODE   READINESS GATES
ollama      ollama-7df7b6f5d-xh68r   0/1     Pending   0          2m22s   <none>   <none>   <none>           <none>
```

<!-- rumdl-enable MD013 -->

Two CloudNativePG pods still held old mounts because they were honoring their
`1800s` termination grace period:

```text
authentik-postgres-1   Terminating   node3
infisical-postgres-1   Terminating   node3
```

They had no finalizers, so they were not force-deleted. After waiting for their
clean shutdown, the stale mount check returned no rows:

```sh
for h in 10.0.0.21 10.0.0.22 10.0.0.23; do
  echo "== $h =="
  ssh "$h" "findmnt -t nfs,nfs4 -o SOURCE,TARGET,FSTYPE | grep 192.168.1.1 || true"
done
```

Observed result:

```text
== 10.0.0.21 ==
== 10.0.0.22 ==
== 10.0.0.23 ==
```

`node3` was then uncordoned:

```sh
kubectl --tls-server-name=node1 uncordon node3
```

Observed result:

```text
node/node3 uncordoned
```

With no stale mounts left, the temporary DNAT was removed from all workers:

<!-- rumdl-disable MD013 -->

```sh
for h in 10.0.0.21 10.0.0.22 10.0.0.23; do
  ssh "$h" 'while sudo iptables -t nat -C OUTPUT -d 192.168.1.1/32 -j DNAT --to-destination 10.0.0.11 2>/dev/null; do
    sudo iptables -t nat -D OUTPUT -d 192.168.1.1/32 -j DNAT --to-destination 10.0.0.11
  done'
done
```

<!-- rumdl-enable MD013 -->

The rule was absent afterward:

```text
== iptables 10.0.0.21 ==
absent
== iptables 10.0.0.22 ==
absent
== iptables 10.0.0.23 ==
absent
```

Final pod and mount checks:

```sh
kubectl --tls-server-name=node1 get pods -A \
  --field-selector=status.phase!=Running,status.phase!=Succeeded -o wide

kubectl --tls-server-name=node1 get pods -A \
  | grep -E 'CrashLoopBackOff|Error|ImagePull|0/' || true

for h in 10.0.0.21 10.0.0.22 10.0.0.23; do
  echo "== mounts $h =="
  ssh "$h" "findmnt -t nfs,nfs4 -o SOURCE,TARGET,FSTYPE | grep 192.168.1.1 || true"
done
```

Observed result:

```text
No resources found

No CrashLoopBackOff, Error, ImagePull, or 0/ready pods were returned.

== mounts 10.0.0.21 ==
== mounts 10.0.0.22 ==
== mounts 10.0.0.23 ==
```

The storage policy was checked again:

```sh
./scripts/check-storage-policy.sh
rg -n "local-path" kubernetes
```

Observed result:

```text
storage policy ok

No local-path references were returned under kubernetes/.
```

After the runtime cleanup, plain `kubectl` failed because the kubeconfig server
was updated to `10.0.0.21`, but the API server certificate still had the old
control-plane IP in its SAN list:

```sh
kubectl get pods -A
```

Observed result:

```text
Unable to connect to the server: tls: failed to verify certificate: x509:
certificate is valid for 10.233.0.1, 192.168.1.11, 127.0.0.1, ::1,
2001:861:5285:37e0:1260:4bff:fe75:4d00, not 10.0.0.21
```

The shortest client-side fix was to keep connecting to `10.0.0.21`, but tell
kubectl to verify the certificate against the old IP that is still present in
the certificate:

```sh
kubectl config set-cluster cluster.local --tls-server-name=192.168.1.11
```

Observed result:

```text
Cluster "cluster.local" set.
```

The resulting kubeconfig cluster entry includes:

```yaml
server: https://10.0.0.21:6443
tls-server-name: 192.168.1.11
```

Plain kubectl access worked afterward:

```sh
kubectl get pods -A --request-timeout=10s
```

Observed result:

```text
Pods were listed successfully without passing --tls-server-name.
```

## Outcome

All Kubernetes PV/PVC objects have been migrated to the NAS IP `10.0.0.11`.

All old `192.168.1.1` NFS mounts were cleared from `node1`, `node2`, and
`node3`.

The temporary DNAT rule has been removed from all three workers.

Plain kubectl access now works through `10.0.0.21`.

All checked pods recovered, and the storage policy check still passes.
