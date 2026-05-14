# 2026-05-14 - Migration du PVC Navidrome vers NFS

## 1. Probleme a resoudre

Navidrome utilisait encore un PVC `local-path` pour ses donnees applicatives:

```text
navidrome/navidrome-data-pvc   Bound   local-path   pvc-cec06eea-febe-44ff-a287-708d814b4584   5Gi
```

Le PV etait attache a `node3`:

```text
storageClassName: local-path
hostPath:
  path: /opt/local-path-provisioner/pvc-cec06eea-febe-44ff-a287-708d814b4584_navidrome_navidrome-data-pvc
nodeAffinity:
  values:
  - node3
```

Si `node3` etait eteinte, Navidrome pouvait perdre l'acces a sa base et rester
bloque comme Traefik l'avait fait. L'objectif etait de migrer
`navidrome-data-pvc` vers le StorageClass partage `nfs-k8s`.

## 2. Cheminement et commandes

Verifier que Forgejo/Argo CD voyait bien le dernier commit avant de continuer:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n argocd get app homelab openwebui navidrome \
  -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,AUTO:.spec.syncPolicy.automated,REV:.status.sync.revision --no-headers
```

Resultat apres refresh:

```text
homelab     OutOfSync   Healthy   <none>                          8a2ae4f37f3cf4ae243eb10b75f0b7f60bca7737
openwebui   Synced      Healthy   <none>                          <none>
navidrome   Synced      Healthy   map[prune:true selfHeal:true]   8a2ae4f37f3cf4ae243eb10b75f0b7f60bca7737
```

Le root `homelab` est reste suspendu pendant la migration pour eviter qu'Argo
CD ne recree l'ancien PVC `local-path`.

Mesurer les donnees a migrer:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome exec deploy/navidrome -- du -sh /data

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome exec deploy/navidrome -- find /data -maxdepth 2 -type f
```

Resultat:

```text
152.4M /data
/data/navidrome.db
/data/navidrome.db-shm
/data/navidrome.db-wal
```

Suspendre temporairement l'auto-sync de Navidrome:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n argocd patch app navidrome --type=merge \
  -p '{"spec":{"syncPolicy":{"automated":null}}}'
```

Modifier le Git desired state:

```yaml
dataStorage:
  pvcName: navidrome-data-pvc
  size: 5Gi
  storageClassName: nfs-k8s
```

Les fichiers modifies sont:

```text
kubernetes/navidrome/values.yaml
kubernetes/navidrome/navidrome.yaml
scripts/storage-policy-local-path-allowlist.txt
```

Arreter Navidrome avant copie pour figer SQLite:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome scale deploy navidrome --replicas=0

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome rollout status deploy/navidrome --timeout=60s
```

Resultat:

```text
deployment.apps/navidrome scaled
deployment "navidrome" successfully rolled out
No resources found in navidrome namespace.
```

Creer un PVC temporaire NFS:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: navidrome-data-nfs-migration
  namespace: navidrome
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: nfs-k8s
```

Creer un pod de copie montant l'ancien PVC en lecture seule et le PVC NFS
temporaire:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: navidrome-pvc-copy
  namespace: navidrome
spec:
  restartPolicy: Never
  containers:
    - name: copy
      image: alpine:3.20
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: old-data
          mountPath: /old
          readOnly: true
        - name: new-data
          mountPath: /new
  volumes:
    - name: old-data
      persistentVolumeClaim:
        claimName: navidrome-data-pvc
    - name: new-data
      persistentVolumeClaim:
        claimName: navidrome-data-nfs-migration
```

Le pod a ete planifie sur `node3`, ce qui etait attendu car l'ancien PV etait
local a `node3`:

```text
navidrome-pvc-copy   1/1   Running   node3
```

Copier les donnees:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome exec navidrome-pvc-copy -- \
  sh -c 'cd /old && tar cf - . | tar xf - -C /new'
```

Une commande de verification a partiellement echoue:

```bash
find /new -maxdepth 1 -type f -printf "%f\n"
```

Resultat:

```text
find: unrecognized: -printf
```

Cause: l'image `alpine` utilise BusyBox `find`, qui ne supporte pas `-printf`.
La verification a ete refaite avec des commandes compatibles BusyBox.

Verifier la copie:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome exec navidrome-pvc-copy -- \
  sh -c 'find /old -type f | wc -l; find /new -type f | wc -l; find /old -type d | wc -l; find /new -type d | wc -l'

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome exec navidrome-pvc-copy -- \
  sh -c 'sha256sum /old/navidrome.db /new/navidrome.db'
```

Resultat:

```text
old-files 1532
new-files 1532
old-dirs 5918
new-dirs 5918
c55f8de13fb2c94a960d1c4c9a412b1eeac81f8b17fd262aab4a0c98b547f0d7  /old/navidrome.db
c55f8de13fb2c94a960d1c4c9a412b1eeac81f8b17fd262aab4a0c98b547f0d7  /new/navidrome.db
```

Supprimer l'ancien PVC puis recreer le PVC final en `nfs-k8s`:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome delete pvc navidrome-data-pvc
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: navidrome-data-pvc
  namespace: navidrome
  annotations:
    argocd.argoproj.io/tracking-id: navidrome:/PersistentVolumeClaim:navidrome/navidrome-data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: nfs-k8s
```

Copier du PVC temporaire NFS vers le PVC final NFS:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome exec navidrome-final-copy -- \
  sh -c 'cd /src && tar cf - . | tar xf - -C /dst && du -sh /src /dst && find /src -type f | wc -l && find /dst -type f | wc -l && sha256sum /src/navidrome.db /dst/navidrome.db'
```

Resultat:

```text
115.4M /src
115.4M /dst
1532
1532
c55f8de13fb2c94a960d1c4c9a412b1eeac81f8b17fd262aab4a0c98b547f0d7  /src/navidrome.db
c55f8de13fb2c94a960d1c4c9a412b1eeac81f8b17fd262aab4a0c98b547f0d7  /dst/navidrome.db
```

Redemarrer Navidrome:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome scale deploy navidrome --replicas=1

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome rollout status deploy/navidrome --timeout=180s
```

Resultat:

```text
deployment.apps/navidrome scaled
deployment "navidrome" successfully rolled out
navidrome-65c94868d7-fkss7   1/1   Running   node3
```

Verifier les logs:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome logs deploy/navidrome --tail=80
```

Resultat important:

```text
Version: 0.60.3
goose: no migrations to run. current version: 20260117201522
Started watcher for library
Executing initial scan
Finished initializing cache
```

Nettoyer le PVC temporaire et son PV:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n navidrome delete pvc navidrome-data-nfs-migration

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  delete pv pvc-8479b546-4704-4a47-9a16-3e3027da6789
```

Le dossier NFS temporaire nettoye etait:

```text
/volume1/k8s/navidrome-navidrome-data-nfs-migration-pvc-8479b546-4704-4a47-9a16-3e3027da6789
```

Une commande de statut a aussi echoue:

```bash
kubectl ... -o custom-columns=NAME:.metadata.name,PHASE:.status.phase,READY:.status.containerStatuses[0].ready
```

Resultat:

```text
zsh:1: no matches found: custom-columns=NAME:.metadata.name,PHASE:.status.phase,READY:.status.containerStatuses[0].ready
```

Cause: `zsh` interprete les crochets de `[0]`. Il faut citer l'argument
`custom-columns` ou echapper les crochets.

## 3. Resultats obtenus

Le PVC final Navidrome est maintenant en NFS:

```text
navidrome-data-pvc   nfs-k8s   Bound   pvc-1f866e9a-7c31-4550-8080-37fda981fe6e   5Gi
navidrome-music-pvc            Bound   navidrome-music-pv                         200Gi
```

Les PVC `local-path` restants dans le cluster sont maintenant:

```text
media/autobrr-config-pvc
media/bazarr-config-pvc
media/nzbget-config-pvc
media/prowlarr-config-pvc
media/qbittorrent-config-pvc
media/radarr-config-pvc
media/sonarr-config-pvc
ollama/ollama-data
sparkyfitness/sparkyfitness-backup-pvc
sparkyfitness/sparkyfitness-db-pvc
sparkyfitness/sparkyfitness-uploads-pvc
```

Le controle de policy local passe:

```bash
./scripts/check-storage-policy.sh
```

```text
storage policy ok
```

## 4. Resultat final et changement necessaire

Navidrome ne depend plus du disque local de `node3` pour ses donnees
applicatives. Le changement durable est dans Git:

```text
kubernetes/navidrome/values.yaml       storageClassName: nfs-k8s
kubernetes/navidrome/navidrome.yaml    storageClassName: nfs-k8s
```

Il faut pousser le commit, synchroniser Forgejo, puis laisser Argo CD reprendre
le desired state `nfs-k8s`. Tant que Forgejo n'a pas le commit, l'auto-sync root
et Navidrome doivent rester suspendus pour eviter un rollback vers `local-path`.
