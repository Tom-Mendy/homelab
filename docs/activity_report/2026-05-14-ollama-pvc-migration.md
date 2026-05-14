# 2026-05-14 - Migration du PVC Ollama vers NFS

## 1. Probleme a resoudre

Ollama utilisait encore un PVC `local-path` pour ses modeles:

```text
ollama/ollama-data   Bound   local-path   pvc-c69d66cc-7e76-43e9-80b4-df6a9ff48ae5   50Gi
```

Le PV etait attache a `node3`:

```text
storageClassName: local-path
hostPath:
  path: /opt/local-path-provisioner/pvc-c69d66cc-7e76-43e9-80b4-df6a9ff48ae5_ollama_ollama-data
nodeAffinity:
  values:
  - node3
```

L'objectif etait de sortir les donnees Ollama du disque local de `node3` et de
les mettre sur le StorageClass partage `nfs-k8s`. Le workload reste lie a un
node GPU pour l'execution, mais les modeles ne sont plus stockes sur un disque
worker-local.

## 2. Cheminement et commandes

Verifier l'etat initial:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama get deploy,pod,pvc -o wide
```

Resultat:

```text
deployment.apps/ollama   1/1
pod/ollama-ffb6c4db4-hpdk8   1/1   Running   node3
persistentvolumeclaim/ollama-data   Bound   local-path   50Gi
```

Mesurer les donnees et lister les modeles:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama exec deploy/ollama -- du -sh /root/.ollama

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama exec deploy/ollama -- ollama list
```

Resultat:

```text
14G /root/.ollama

NAME              ID              SIZE
deepseek-r1:8b    6995872bfe4c    5.2 GB
gemma4:e4b        c6eb396dbd59    9.6 GB
```

Suspendre Argo CD pour eviter un rollback pendant la suppression/recreation du
PVC:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n argocd patch app homelab --type=merge \
  -p '{"spec":{"syncPolicy":{"automated":null}}}'

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n argocd patch app ollama --type=merge \
  -p '{"spec":{"syncPolicy":{"automated":null}}}'
```

Modifier le desired state Git:

```yaml
persistence:
  enabled: true
  storageClass: nfs-k8s
  size: 50Gi
```

Les fichiers modifies sont:

```text
kubernetes/ollama/values.yaml
scripts/storage-policy-local-path-allowlist.txt
```

Arreter Ollama:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama scale deploy ollama --replicas=0

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama wait --for=delete pod -l app=ollama --timeout=120s
```

Creer un PVC temporaire NFS:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ollama-data-nfs-migration
  namespace: ollama
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: nfs-k8s
```

Creer un pod de copie sur `node3`, car l'ancien PV etait local a `node3`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ollama-pvc-copy
  namespace: ollama
spec:
  nodeSelector:
    kubernetes.io/hostname: node3
  containers:
    - name: copy
      image: alpine:3.20
      command: ["sh", "-c", "sleep 7200"]
      volumeMounts:
        - name: old-data
          mountPath: /old
          readOnly: true
        - name: new-data
          mountPath: /new
```

Copier vers le PVC temporaire:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama exec ollama-pvc-copy -- \
  sh -c 'cd /old && tar cf - . | tar xf - -C /new'
```

Resultat de copie temporaire:

```text
old 13.8G
new 13.6G
old-files 13
new-files 13
old-dirs 8
new-dirs 8
```

Faire un checksum complet des 13 fichiers:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama exec ollama-pvc-copy -- \
  sh -c 'cd /old && find . -type f | sort | while read f; do sha256sum "$f"; done > /tmp/ollama.old; cd /new && find . -type f | sort | while read f; do sha256sum "$f"; done > /tmp/ollama.new; diff -u /tmp/ollama.old /tmp/ollama.new'
```

Resultat:

```text
13 /tmp/ollama.old
13 /tmp/ollama.new
checksum-ok
```

Supprimer l'ancien PVC local-path et recreer le PVC final en NFS:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama delete pvc ollama-data
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ollama-data
  namespace: ollama
  annotations:
    argocd.argoproj.io/tracking-id: ollama:/PersistentVolumeClaim:ollama/ollama-data
  labels:
    app.kubernetes.io/instance: ollama
    app.kubernetes.io/name: ollama
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: nfs-k8s
```

Copier du PVC temporaire vers le PVC final:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama exec ollama-final-copy -- \
  sh -c 'cd /src && tar cf - . | tar xf - -C /dst'
```

Resultat de copie finale:

```text
src 13.8G
dst 13.6G
src-files 13
dst-files 13
src-dirs 8
dst-dirs 8
checksum-ok
```

Redemarrer Ollama:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama scale deploy ollama --replicas=1

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama rollout status deploy/ollama --timeout=600s
```

Resultat:

```text
deployment "ollama" successfully rolled out
pod/ollama-ffb6c4db4-zjv79   1/1   Running   node3
```

Verifier les logs:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama logs deploy/ollama --tail=80
```

Resultat important:

```text
total blobs: 9
Listening on [::]:11434 (version 0.20.5)
inference compute ... library=CUDA ... name=CUDA0 ... NVIDIA GeForce GTX 1080
```

Verifier les modeles apres migration:

```bash
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n ollama exec deploy/ollama -- ollama list
```

Resultat:

```text
deepseek-r1:8b    6995872bfe4c    5.2 GB
gemma4:e4b        c6eb396dbd59    9.6 GB
```

Nettoyer le PVC/PV temporaire et le dossier NFS temporaire:

```text
PVC temporaire: ollama-data-nfs-migration
PV temporaire: pvc-f2689bea-edd9-454a-bd30-ea509fe303d2
Dossier NFS: /volume1/k8s/ollama-ollama-data-nfs-migration-pvc-f2689bea-edd9-454a-bd30-ea509fe303d2
```

## 3. Resultats obtenus

Le PVC final Ollama est maintenant en NFS:

```text
ollama-data   Bound   nfs-k8s   pvc-ae8750bd-2c37-4cc2-a4e5-dec9c8aecf93   50Gi
```

Ollama est disponible:

```text
deployment.apps/ollama   1/1
pod/ollama-ffb6c4db4-zjv79   1/1   Running
```

Le controle de policy passe:

```bash
./scripts/check-storage-policy.sh
```

```text
storage policy ok
```

Il ne reste plus de `local-path` dans les manifests actifs sous `kubernetes/`.
Les seuls PVC `local-path` encore visibles dans le cluster sont ceux de
`sparkyfitness`, qui ne sont pas geres par les manifests trouves dans ce depot:

```text
sparkyfitness/sparkyfitness-backup-pvc
sparkyfitness/sparkyfitness-db-pvc
sparkyfitness/sparkyfitness-uploads-pvc
```

## 4. Resultat final et changement necessaire

Le stockage des modeles Ollama ne depend plus du disque local de `node3`.
Le changement durable est:

```text
kubernetes/ollama/values.yaml
  persistence.storageClass: nfs-k8s

scripts/storage-policy-local-path-allowlist.txt
  fichier vide
```

Important: l'execution Ollama reste dependante d'un node GPU. Cette migration
resout le stockage local, mais pas la dependance compute a `node3` tant qu'il
n'y a pas un autre worker avec GPU et label compatible.

Il faut pousser le commit, synchroniser Forgejo, puis reactiver l'auto-sync Argo
pour `homelab` et `ollama`. Tant que Forgejo n'a pas recupere le commit,
`homelab` et `ollama` doivent rester sans auto-sync pour eviter un rollback vers
`local-path`.
