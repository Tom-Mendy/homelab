# Talos storage audit before cluster rebuild

<!-- rumdl-disable MD013 -->

## Problem

The Ubuntu Kubernetes cluster will be replaced by a clean Talos cluster. Before
that rebuild, persistent data must not depend on worker-local disks, and dynamic
NFS PVCs must be rebound to their existing Synology paths instead of creating
empty new directories.

## Reasoning

The repository policy already forbids `local-path` for workloads. The live
cluster still has a `local-path` StorageClass and provisioner pod installed, but
no active PVC uses it. All active persistent data is either:

- dynamic `nfs-k8s` under `10.0.0.11:/volume1/k8s`;
- static Synology NFS PVs for fixed paths such as Forgejo, Prometheus,
  Vaultwarden, Navidrome music, and media libraries.

For Talos restore, Kubernetes object UIDs do not need to match. The critical
restore identity is:

- namespace;
- PVC name;
- PV name from `spec.volumeName`;
- NFS server and path.

## Commands and results

Repository storage policy:

```sh
./scripts/check-storage-policy.sh
```

Result:

```text
storage policy ok
```

Search for forbidden `local-path` manifests:

```sh
rg -n "local-path" kubernetes --glob '*.yaml' --glob '*.yml'
```

Result: no matches.

Cluster nodes:

```sh
kubectl get nodes -o wide
```

Result:

```text
NAME    STATUS   ROLES           VERSION   INTERNAL-IP   OS-IMAGE
node1   Ready    control-plane   v1.34.3   10.0.0.21     Ubuntu 24.04.4 LTS
node2   Ready    <none>          v1.34.3   10.0.0.22     Ubuntu 24.04.4 LTS
node3   Ready    <none>          v1.34.3   10.0.0.23     Ubuntu 24.04.4 LTS
```

Storage classes:

```sh
kubectl get storageclass -o wide
```

Result:

```text
NAME         PROVISIONER                                                     RECLAIMPOLICY   VOLUMEBINDINGMODE
local-path   rancher.io/local-path                                           Delete          WaitForFirstConsumer
nfs-k8s      cluster.local/nfs-provisioner-nfs-subdir-external-provisioner   Retain          Immediate
```

PVC inventory:

```sh
kubectl get pvc -A -o custom-columns='NS:.metadata.namespace,PVC:.metadata.name,STATUS:.status.phase,SC:.spec.storageClassName,VOLUME:.spec.volumeName,CAPACITY:.status.capacity.storage,ACCESS:.status.accessModes[*]'
```

Result:

```text
NS                PVC                                                   STATUS   SC        VOLUME                                               CAPACITY   ACCESS
atuin             atuin-config-v2                                       Bound    nfs-k8s   pvc-717898a7-6a05-4e19-91d7-34dbb26be28f             20Gi       ReadWriteMany
atuin             postgres-data-v2                                      Bound    nfs-k8s   pvc-a6b539a0-fd00-4f21-af94-33bbd1edc006             10Gi       ReadWriteOnce
authentik         authentik-postgres-1                                  Bound    nfs-k8s   pvc-838dd586-f332-46ea-b676-84a72bbad01b             10Gi       ReadWriteOnce
forgejo           forgejo-data-pvc                                      Bound              forgejo-data-pv                                      20Gi       ReadWriteMany
grafana           grafana                                               Bound    nfs-k8s   pvc-2f17a00c-06b7-4e07-a189-d1b15b21078f             5Gi        ReadWriteOnce
infisical         infisical-postgres-1                                  Bound    nfs-k8s   pvc-1eba9e7c-525a-4ef6-ab57-64a76d593e5d             10Gi       ReadWriteOnce
infisical         redis-data-redis-master-0                             Bound    nfs-k8s   pvc-8354a8fd-e805-4076-b641-5204b8665656             5Gi        ReadWriteOnce
media             autobrr-config-pvc                                    Bound    nfs-k8s   pvc-970bdcaf-769c-4dd9-8a00-db0f8e57a9c8             5Gi        ReadWriteOnce
media             bazarr-config-pvc                                     Bound    nfs-k8s   pvc-c987d9c0-827e-4eff-a30f-da8381ae992e             5Gi        ReadWriteOnce
media             media-downloads-pvc                                   Bound              media-downloads-pv                                   2Ti        ReadWriteMany
media             media-movies-pvc                                      Bound              media-movies-pv                                      4Ti        ReadWriteMany
media             media-series-pvc                                      Bound              media-series-pv                                      4Ti        ReadWriteMany
media             nzbget-config-pvc                                     Bound    nfs-k8s   pvc-e119f4ef-5a79-4ea5-aeb9-2751d913241b             5Gi        ReadWriteOnce
media             prowlarr-config-pvc                                   Bound    nfs-k8s   pvc-04fa3812-ab36-4e02-84d2-0c21aa8189a6             5Gi        ReadWriteOnce
media             qbittorrent-config-pvc                                Bound    nfs-k8s   pvc-6f588b16-79b2-437b-8c90-8bcf180e93e4             5Gi        ReadWriteOnce
media             radarr-config-pvc                                     Bound    nfs-k8s   pvc-128e3b8f-3e21-4132-a4fa-5f62e09b9265             5Gi        ReadWriteOnce
media             sonarr-config-pvc                                     Bound    nfs-k8s   pvc-77b861ce-af03-4614-ba7d-cce0d9394aec             5Gi        ReadWriteOnce
navidrome         navidrome-data-pvc                                    Bound    nfs-k8s   pvc-1f866e9a-7c31-4550-8080-37fda981fe6e             5Gi        ReadWriteOnce
navidrome         navidrome-music-pvc                                   Bound              navidrome-music-pv                                   200Gi      ReadOnlyMany
nfs-provisioner   pvc-nfs-provisioner-nfs-subdir-external-provisioner   Bound              pv-nfs-provisioner-nfs-subdir-external-provisioner   10Mi       ReadWriteMany
ollama            ollama-data                                           Bound    nfs-k8s   pvc-ae8750bd-2c37-4cc2-a4e5-dec9c8aecf93             50Gi       ReadWriteOnce
openwebui         open-webui                                            Bound    nfs-k8s   pvc-090fcf5b-66f0-457f-9279-f5167b075af5             50Gi       ReadWriteOnce
prometheus        prometheus-server-pvc                                 Bound              prometheus-server-pv                                 50Gi       ReadWriteMany
traefik           traefik                                               Bound    nfs-k8s   pvc-996dfbae-13a1-4357-8aba-17c65fce8409             128Mi      ReadWriteOnce
vaultwarden       vaultwarden-data-pvc                                  Bound              vaultwarden-data-pv                                  10Gi       ReadWriteMany
```

PV to NFS path inventory for Talos restore:

```sh
kubectl get pv -o custom-columns='PV:.metadata.name,STATUS:.status.phase,SC:.spec.storageClassName,SERVER:.spec.nfs.server,PATH:.spec.nfs.path,CLAIM:.spec.claimRef.namespace/.spec.claimRef.name,RECLAIM:.spec.persistentVolumeReclaimPolicy'
```

Result:

```text
PV                                                   STATUS      SC        SERVER      PATH                                                                                        RECLAIM
forgejo-data-pv                                      Bound       <none>    10.0.0.11   /volume1/forgejo                                                                            Retain
media-downloads-pv                                   Bound       <none>    10.0.0.11   /volume1/Downloads                                                                          Retain
media-movies-pv                                      Bound       <none>    10.0.0.11   /volume1/video/Film                                                                         Retain
media-series-pv                                      Bound       <none>    10.0.0.11   /volume1/video/Serie                                                                        Retain
navidrome-music-pv                                   Bound       <none>    10.0.0.11   /volume1/music                                                                              Retain
prometheus-server-pv                                 Bound       <none>    10.0.0.11   /volume1/prometheus                                                                         Retain
pv-nfs-provisioner-nfs-subdir-external-provisioner   Bound       <none>    10.0.0.11   /volume1/k8s                                                                                Retain
pvc-04fa3812-ab36-4e02-84d2-0c21aa8189a6             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/media-prowlarr-config-pvc-pvc-04fa3812-ab36-4e02-84d2-0c21aa8189a6             Retain
pvc-090fcf5b-66f0-457f-9279-f5167b075af5             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/openwebui-open-webui-pvc-090fcf5b-66f0-457f-9279-f5167b075af5                  Retain
pvc-128e3b8f-3e21-4132-a4fa-5f62e09b9265             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/media-radarr-config-pvc-pvc-128e3b8f-3e21-4132-a4fa-5f62e09b9265               Retain
pvc-1eba9e7c-525a-4ef6-ab57-64a76d593e5d             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/infisical-infisical-postgres-1-pvc-1eba9e7c-525a-4ef6-ab57-64a76d593e5d        Retain
pvc-1f866e9a-7c31-4550-8080-37fda981fe6e             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/navidrome-navidrome-data-pvc-pvc-1f866e9a-7c31-4550-8080-37fda981fe6e          Retain
pvc-2f17a00c-06b7-4e07-a189-d1b15b21078f             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/grafana-grafana-pvc-2f17a00c-06b7-4e07-a189-d1b15b21078f                       Retain
pvc-6f588b16-79b2-437b-8c90-8bcf180e93e4             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/media-qbittorrent-config-pvc-pvc-6f588b16-79b2-437b-8c90-8bcf180e93e4          Retain
pvc-717898a7-6a05-4e19-91d7-34dbb26be28f             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/atuin-atuin-config-v2-pvc-717898a7-6a05-4e19-91d7-34dbb26be28f                 Retain
pvc-77b861ce-af03-4614-ba7d-cce0d9394aec             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/media-sonarr-config-pvc-pvc-77b861ce-af03-4614-ba7d-cce0d9394aec               Retain
pvc-8354a8fd-e805-4076-b641-5204b8665656             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/infisical-redis-data-redis-master-0-pvc-8354a8fd-e805-4076-b641-5204b8665656   Retain
pvc-838dd586-f332-46ea-b676-84a72bbad01b             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/authentik-authentik-postgres-1-pvc-838dd586-f332-46ea-b676-84a72bbad01b        Retain
pvc-970bdcaf-769c-4dd9-8a00-db0f8e57a9c8             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/media-autobrr-config-pvc-pvc-970bdcaf-769c-4dd9-8a00-db0f8e57a9c8              Retain
pvc-996dfbae-13a1-4357-8aba-17c65fce8409             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/traefik-traefik-pvc-996dfbae-13a1-4357-8aba-17c65fce8409                       Retain
pvc-a6b539a0-fd00-4f21-af94-33bbd1edc006             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/atuin-postgres-data-v2-pvc-a6b539a0-fd00-4f21-af94-33bbd1edc006                Retain
pvc-ae8750bd-2c37-4cc2-a4e5-dec9c8aecf93             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/ollama-ollama-data-pvc-ae8750bd-2c37-4cc2-a4e5-dec9c8aecf93                    Retain
pvc-c987d9c0-827e-4eff-a30f-da8381ae992e             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/media-bazarr-config-pvc-pvc-c987d9c0-827e-4eff-a30f-da8381ae992e               Retain
pvc-e119f4ef-5a79-4ea5-aeb9-2751d913241b             Bound       nfs-k8s   10.0.0.11   /volume1/k8s/media-nzbget-config-pvc-pvc-e119f4ef-5a79-4ea5-aeb9-2751d913241b               Retain
vaultwarden-data-pv                                  Bound       <none>    10.0.0.11   /volume1/vaultwarden                                                                        Retain
```

Node affinity check:

```sh
kubectl get pv -o jsonpath='{range .items[?(@.spec.nodeAffinity)]}{.metadata.name}{"\n"}{end}'
```

Result: no PV had node affinity.

Scheduling constraints:

```sh
kubectl get deploy,sts -A -o json | jq -r '.items[] | select(.spec.template.spec.nodeSelector or .spec.template.spec.affinity or .spec.template.spec.tolerations) | [.kind, .metadata.namespace, .metadata.name, (.spec.template.spec.nodeSelector // {} | tostring), (.spec.template.spec.affinity // {} | tostring)] | @tsv'
```

Important result:

```text
Deployment ollama ollama {"gpu":"true"} {}
```

Most other constraints were OS selectors or preferred anti-affinity. Ollama is
intentionally tied to the GPU label, currently on `node3`.

Pod disruption budgets:

```sh
kubectl get pdb -A -o wide
```

Result:

```text
NAMESPACE   NAME                         MIN AVAILABLE   ALLOWED DISRUPTIONS
authentik   authentik-postgres-primary   1               0
infisical   infisical-postgres-primary   1               0
```

Drain dry-run for `node3`:

```sh
kubectl drain node3 --ignore-daemonsets --delete-emptydir-data --dry-run=server
```

Result:

```text
node/node3 cordoned (server dry run)
evicting pod vaultwarden/vaultwarden-7d7954489c-fxfps (server dry run)
evicting pod blocky/blocky-75bbb9f875-r2r5f (server dry run)
evicting pod ollama/ollama-7df7b6f5d-xh68r (server dry run)
evicting pod forgejo/forgejo-f8df4888c-5htv6 (server dry run)
evicting pod grafana/grafana-59b46dbb4d-lj7qw (server dry run)
evicting pod prometheus/prometheus-server-8488c665c6-kcj6k (server dry run)
node/node3 drained (server dry run)
```

Drain dry-run for `node2`:

```sh
kubectl drain node2 --ignore-daemonsets --delete-emptydir-data --dry-run=server
```

Result:

```text
node/node2 cordoned (server dry run)
error when evicting pods/"authentik-postgres-1" -n "authentik": Cannot evict pod as it would violate the pod's disruption budget.
error when evicting pods/"infisical-postgres-1" -n "infisical": Cannot evict pod as it would violate the pod's disruption budget.
```

The command was interrupted because the dry-run kept retrying those PDB-blocked
evictions.

## Final outcome

The storage policy is ready for a Talos rebuild:

- no active manifest under `kubernetes/` uses `local-path`;
- no active PV has node affinity;
- all active persistent workload data is on Synology NFS;
- the exact dynamic `nfs-k8s` PV names and paths are recorded above.

The Talos migration will use controlled downtime for the single-instance
CloudNativePG clusters used by Authentik and Infisical. Their PDBs correctly
block normal eviction because there is no standby instance. During the
maintenance window, drain `node2` with `--disable-eviction`, then verify both
database pods restart on another schedulable node and both CloudNativePG
clusters return to healthy state.

The selected runbook is:

```sh
kubectl get clusters.postgresql.cnpg.io -A -o wide
kubectl get pdb -A -o wide
kubectl drain node2 \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --disable-eviction
kubectl get pods -n authentik -o wide
kubectl get pods -n infisical -o wide
kubectl get clusters.postgresql.cnpg.io -A -o wide
```

For the new Talos cluster, recreate static PV bindings for the dynamic NFS paths
before allowing Argo CD or Helm to create fresh PVCs. Otherwise the NFS
provisioner will create new empty directories under `/volume1/k8s`.
