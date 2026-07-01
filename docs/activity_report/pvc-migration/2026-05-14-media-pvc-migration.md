# 2026-05-14 - Migration des PVC media config vers NFS

## 1. Probleme a resoudre

Les sept applications du namespace `media` utilisaient encore des PVC
`local-path` pour leurs configurations applicatives:

```text
media/autobrr-config-pvc       local-path   node3
media/bazarr-config-pvc        local-path   node2
media/nzbget-config-pvc        local-path   node3
media/prowlarr-config-pvc      local-path   node3
media/qbittorrent-config-pvc   local-path   node3
media/radarr-config-pvc        local-path   node2
media/sonarr-config-pvc        local-path   node3
```

Ces PVC etaient attaches aux disques locaux des workers. Une extinction de
`node2` ou `node3` pouvait donc bloquer une partie des services media. Les PV
NFS statiques `media-downloads-pvc`, `media-movies-pvc` et `media-series-pvc`
etaient deja conformes et n'ont pas ete modifies.

## 2. Cheminement et commandes

Verifier les apps et PVC existants:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media get deploy,pod,pvc -o wide
```

Resultat important:

```text
autobrr-config-pvc       Bound   local-path   pvc-28637192-bf06-4111-aee5-4f76442f0cfb
bazarr-config-pvc        Bound   local-path   pvc-e0c6e1ce-d9d4-489c-847d-2d8d92daf149
nzbget-config-pvc        Bound   local-path   pvc-a66dc365-6c16-4a7e-a476-7111cd5f8d77
prowlarr-config-pvc      Bound   local-path   pvc-4f37af43-0e03-4dfc-b13f-02910556478d
qbittorrent-config-pvc   Bound   local-path   pvc-adc762dc-ef9b-4ae2-8119-569d426d41ca
radarr-config-pvc        Bound   local-path   pvc-b200c378-d118-4049-ae23-6e9dd7a04459
sonarr-config-pvc        Bound   local-path   pvc-849f8a14-6f38-4124-b84a-0339c50297cc
```

Verifier les nodes des anciens PV:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab get pv \
  pvc-28637192-bf06-4111-aee5-4f76442f0cfb \
  pvc-e0c6e1ce-d9d4-489c-847d-2d8d92daf149 \
  pvc-a66dc365-6c16-4a7e-a476-7111cd5f8d77 \
  pvc-4f37af43-0e03-4dfc-b13f-02910556478d \
  pvc-adc762dc-ef9b-4ae2-8119-569d426d41ca \
  pvc-b200c378-d118-4049-ae23-6e9dd7a04459 \
  pvc-849f8a14-6f38-4124-b84a-0339c50297cc \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.claimRef.name}{"\t"}{.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]}{"\n"}{end}'
```

Resultat:

```text
pvc-28637192-bf06-4111-aee5-4f76442f0cfb   autobrr-config-pvc       node3
pvc-e0c6e1ce-d9d4-489c-847d-2d8d92daf149   bazarr-config-pvc        node2
pvc-a66dc365-6c16-4a7e-a476-7111cd5f8d77   nzbget-config-pvc        node3
pvc-4f37af43-0e03-4dfc-b13f-02910556478d   prowlarr-config-pvc      node3
pvc-adc762dc-ef9b-4ae2-8119-569d426d41ca   qbittorrent-config-pvc   node3
pvc-b200c378-d118-4049-ae23-6e9dd7a04459   radarr-config-pvc        node2
pvc-849f8a14-6f38-4124-b84a-0339c50297cc   sonarr-config-pvc        node3
```

Mesurer les volumes avant migration:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec deploy/autobrr -- du -sh /config
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec deploy/bazarr -- du -sh /config
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec deploy/nzbget -c nzbget -- du -sh /config
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec deploy/prowlarr -- du -sh /config
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec deploy/qbittorrent -c qbittorrent -- du -sh /config
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec deploy/radarr -- du -sh /config
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec deploy/sonarr -- du -sh /config
```

Resultat:

```text
autobrr       700.0K
bazarr        492K
nzbget        100K
prowlarr      35M
qbittorrent   13M
radarr        66M
sonarr        72M
```

Suspendre Argo CD:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n argocd patch app homelab --type=merge \
  -p '{"spec":{"syncPolicy":{"automated":null}}}'

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n argocd patch app media --type=merge \
  -p '{"spec":{"syncPolicy":{"automated":null}}}'
```

Un premier arret a ete annule car `media` avait ete remis en auto-sync par le
root Argo. Il a fallu verifier explicitement:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n argocd get app homelab media \
  -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,\
HEALTH:.status.health.status,AUTO:.spec.syncPolicy.automated,\
REV:.status.sync.revision \
  --no-headers
```

Resultat attendu avant de continuer:

```text
homelab   OutOfSync   Healthy   <none>   92e19c79e2ff3a4bfdc9e0a75e69a7589f173d3c
media     Synced      Healthy   <none>   92e19c79e2ff3a4bfdc9e0a75e69a7589f173d3c
```

Modifier le desired state Git:

```yaml
configStorage:
  className: nfs-k8s
  defaultSize: 5Gi
```

Fichiers modifies:

```text
kubernetes/media/values.yaml
scripts/storage-policy-local-path-allowlist.txt
```

Arreter les services:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media scale deploy autobrr bazarr nzbget prowlarr qbittorrent \
  radarr sonarr --replicas=0
```

Creer sept PVC temporaires `nfs-k8s`:

```text
autobrr-config-nfs-migration
bazarr-config-nfs-migration
nzbget-config-nfs-migration
prowlarr-config-nfs-migration
qbittorrent-config-nfs-migration
radarr-config-nfs-migration
sonarr-config-nfs-migration
```

Creer deux pods de copie, car les anciens volumes etaient sur deux nodes:

```text
media-pvc-copy-node2   node2   bazarr, radarr
media-pvc-copy-node3   node3   autobrr, nzbget, prowlarr, qbittorrent, sonarr
```

Copier les donnees vers les PVC temporaires:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec media-pvc-copy-node2 -- \
  sh -c 'for app in bazarr radarr; do
    cd /old/$app && tar cf - . | tar xf - -C /new/$app
  done'

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec media-pvc-copy-node3 -- \
  sh -c 'for app in autobrr nzbget prowlarr qbittorrent sonarr; do
    cd /old/$app && tar cf - . | tar xf - -C /new/$app
  done'
```

Verifier les copies temporaires:

```text
bazarr        15 fichiers source, 15 fichiers destination
radarr        96 fichiers source, 96 fichiers destination
autobrr       3 fichiers source, 3 fichiers destination
nzbget        2 fichiers source, 2 fichiers destination
prowlarr      618 fichiers source, 618 fichiers destination
qbittorrent   139 fichiers source, 139 fichiers destination
sonarr        128 fichiers source, 128 fichiers destination
```

Checksums:

```text
bazarr checksum ok
radarr checksum ok
autobrr checksum ok
nzbget checksum ok
prowlarr checksum ok
qbittorrent checksum ok
sonarr checksum ok
```

Supprimer les anciens PVC `local-path`, puis recreer les PVC finaux avec les
memes noms et `storageClassName: nfs-k8s`.

Copier des PVC temporaires vers les PVC finaux:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media exec media-final-copy -- \
  sh -c 'for app in autobrr bazarr nzbget prowlarr qbittorrent radarr sonarr; do
    cd /src/$app && tar cf - . | tar xf - -C /dst/$app
  done'
```

Verification finale de copie:

```text
autobrr       644.0K -> 644.0K, 3 fichiers, checksum ok
bazarr        464.0K -> 464.0K, 15 fichiers, checksum ok
nzbget        80.0K -> 80.0K, 2 fichiers, checksum ok
prowlarr      34.3M -> 34.3M, 618 fichiers, checksum ok
qbittorrent   12.3M -> 12.3M, 139 fichiers, checksum ok
radarr        63.9M -> 63.9M, 96 fichiers, checksum ok
sonarr        71.2M -> 71.2M, 128 fichiers, checksum ok
```

Redemarrer les services:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n media scale deploy autobrr bazarr nzbget prowlarr qbittorrent \
  radarr sonarr --replicas=1
```

Resultat:

```text
autobrr       1/1 Running
bazarr        1/1 Running
nzbget        2/2 Running
prowlarr      1/1 Running
qbittorrent   2/2 Running
radarr        1/1 Running
sonarr        1/1 Running
```

Nettoyer les PVC/PV temporaires et leurs repertoires NFS. La commande suivante
a expire:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n nfs-provisioner wait --for=condition=Ready pod/media-nfs-cleanup --timeout=60s
```

Resultat:

```text
error: timed out waiting for the condition on pods/media-nfs-cleanup
```

Ce n'etait pas un echec du nettoyage: le pod etait deja `Completed`, donc il
n'etait plus `Ready`.

```text
media-nfs-cleanup   0/1   Completed   0
```

## 3. Resultats obtenus

Les sept PVC config `media` sont maintenant en `nfs-k8s`:

```text
autobrr-config-pvc       nfs-k8s   Bound   pvc-970bdcaf-769c-4dd9-8a00-db0f8e57a9c8
bazarr-config-pvc        nfs-k8s   Bound   pvc-c987d9c0-827e-4eff-a30f-da8381ae992e
nzbget-config-pvc        nfs-k8s   Bound   pvc-e119f4ef-5a79-4ea5-aeb9-2751d913241b
prowlarr-config-pvc      nfs-k8s   Bound   pvc-04fa3812-ab36-4e02-84d2-0c21aa8189a6
qbittorrent-config-pvc   nfs-k8s   Bound   pvc-6f588b16-79b2-437b-8c90-8bcf180e93e4
radarr-config-pvc        nfs-k8s   Bound   pvc-128e3b8f-3e21-4132-a4fa-5f62e09b9265
sonarr-config-pvc        nfs-k8s   Bound   pvc-77b861ce-af03-4614-ba7d-cce0d9394aec
```

Les Deployments media sont tous disponibles:

```text
autobrr       1/1
bazarr        1/1
nzbget        1/1 deployment, pod 2/2
prowlarr      1/1
qbittorrent   1/1 deployment, pod 2/2
radarr        1/1
sonarr        1/1
```

Logs lus apres migration:

```text
qBittorrent: WebUI listening on port 8080
NZBGet: using /config/nzbget.conf, listening on 6789
Autobrr: database schema up to date, API listening on 7474
Bazarr: started and waiting for requests on 6767
Prowlarr: application started on 9696
Sonarr: application started on 8989
```

Radarr a logge une erreur de connexion a qBittorrent pendant le redemarrage:

```text
Connection refused (qbittorrent.media.svc.cluster.local:8080)
```

Cette erreur est coherente avec le demarrage simultane des services: qBittorrent
n'etait pas encore pret au moment du healthcheck Radarr, puis qBittorrent a
ensuite confirme que sa WebUI etait disponible.

Le controle de policy passe:

```bash
./scripts/check-storage-policy.sh
```

```text
storage policy ok
```

Les PVC `local-path` restants dans le cluster apres cette migration sont:

```text
ollama/ollama-data
sparkyfitness/sparkyfitness-backup-pvc
sparkyfitness/sparkyfitness-db-pvc
sparkyfitness/sparkyfitness-uploads-pvc
```

## 4. Resultat final et changement necessaire

Les configs media ne dependent plus de `node2` ou `node3`. Le changement durable
est:

```text
kubernetes/media/values.yaml
  configStorage.className: nfs-k8s

scripts/storage-policy-local-path-allowlist.txt
  retrait de kubernetes/media/values.yaml
```

Il faut pousser le commit, synchroniser Forgejo, puis reactiver l'auto-sync Argo
pour `homelab` et `media`. Tant que Forgejo n'a pas recupere le commit,
`homelab` et `media` doivent rester sans auto-sync pour eviter un rollback vers
`local-path`.
