# Veille DevOps / Homelab — GitOps & sécurité

Date UTC: 2026-06-03T06:23:33Z

## Tâche choisie

Axe aléatoire retenu: **GitOps security**. Objectif: transformer un peu de surplus quota en une veille actionnable pour le homelab Kubernetes/Talos de Tom, sans lecture de quota ni manipulation de secrets.

## Signaux surveillés

### 1. Kubernetes

- Dernières releases vues via GitHub API:
  - `v1.36.1` — 2026-05-12 — <https://github.com/kubernetes/kubernetes/releases/tag/v1.36.1>
  - `v1.35.5` — 2026-05-12 — <https://github.com/kubernetes/kubernetes/releases/tag/v1.35.5>
  - `v1.34.8` — 2026-05-12 — <https://github.com/kubernetes/kubernetes/releases/tag/v1.34.8>
- Point d’attention: consulter le changelog de la branche cible avant upgrade; le fichier `CHANGELOG-1.36.md` expose des sections `Urgent Upgrade Notes`.
- Source changelog: <https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.36.md>

### 2. Talos

- Releases vues:
  - `v1.14.0-alpha.1` — 2026-05-28 — <https://github.com/siderolabs/talos/releases/tag/v1.14.0-alpha.1>
  - `v1.13.3` — 2026-05-26 — <https://github.com/siderolabs/talos/releases/tag/v1.13.3>
  - `v1.12.8` — 2026-05-22 — <https://github.com/siderolabs/talos/releases/tag/v1.12.8>
- Pour un homelab stable, préférer une release stable (`v1.13.3` ou branche stable équivalente), pas l’alpha.
- `v1.13.3` embarque notamment: Linux `6.18.33`, Kubernetes `1.36.1`, containerd `2.2.4`, Go `1.26.3`.
- Signal sécurité intéressant dans les commits Talos `v1.13.3`: `feat: redact more machine config secrets and audit redactors`.
- Source: <https://github.com/siderolabs/talos/releases/tag/v1.13.3>

### 3. Flux

- Dernière release vue: `v2.8.8` — 2026-05-20 — <https://github.com/fluxcd/flux2/releases/tag/v2.8.8>
- Points notables:
  - correction d’un risque de fetch d’artefact bloquant indéfiniment côté `helm-controller`;
  - correction d’une croissance mémoire non bornée liée au wrapper retry Kubernetes client;
  - mise à jour `go-git` vers `v5.19.1`, corrigeant `CVE-2026-45571` et `CVE-2026-45570`.
- Source procédure upgrade Flux v2.7+: <https://github.com/fluxcd/flux2/discussions/5572>

### 4. Argo CD

- Dernières releases vues:
  - `v3.4.3` — 2026-05-28 — <https://github.com/argoproj/argo-cd/releases/tag/v3.4.3>
  - `v3.3.11` — 2026-05-28 — <https://github.com/argoproj/argo-cd/releases/tag/v3.3.11>
  - `v3.2.12` — 2026-05-13 — <https://github.com/argoproj/argo-cd/releases/tag/v3.2.12>
- `v3.4.3` est surtout présenté comme bugfix; vérifier la page `Upgrading` avant tout saut majeur/minor.
- Source: <https://github.com/argoproj/argo-cd/releases/tag/v3.4.3>

### 5. Cilium

- Releases vues:
  - `v1.20.0-pre.3` — 2026-06-02 — <https://github.com/cilium/cilium/releases/tag/v1.20.0-pre.3>
  - `v1.19.4` — 2026-05-13 — <https://github.com/cilium/cilium/releases/tag/v1.19.4>
  - `v1.18.10` — 2026-05-13 — <https://github.com/cilium/cilium/releases/tag/v1.18.10>
- Pour un homelab stable, rester sur stable (`1.19.x`/`1.18.x` selon compatibilité cluster), pas `pre`.
- `v1.19.4` contient plusieurs bugfixes réseau utiles: masquerading iptables, egress gateway, IPsec trace, clustermesh EndpointSlice watch.
- Source: <https://github.com/cilium/cilium/releases/tag/v1.19.4>

## Audit local rapide de l’environnement Hermes

Commande exécutée: détection non intrusive des CLI DevOps (`command -v` + tentative courte de version). Aucun fichier de credentials n’a été lu.

- Absents ici: `kubectl`, `talosctl`, `helm`, `kustomize`, `flux`, `argocd`, `kind`, `k3d`, `minikube`, `podman`, `sops`, `age`, `gitleaks`, `trivy`, `cosign`, `syft`, `grype`.
- Présent ici: `docker` dans `/usr/bin/docker`, mais la tentative `docker version --client` a renvoyé `unknown flag: --client`.

Conclusion: cette exécution ne pouvait pas vérifier un vrai cluster homelab depuis Hermes. La valeur ajoutée produite est donc une veille + checklist, pas un audit live du cluster.

## Checklist actionnable pour Tom

### Avant upgrade Talos/Kubernetes

1. Identifier la version actuelle de chaque composant sans afficher de secrets:
   - `talosctl version --nodes <node>`
   - `kubectl version`
   - `kubectl get nodes -o wide`
2. Lire les `Urgent Upgrade Notes` de Kubernetes pour la branche cible.
3. Vérifier la compatibilité CNI/CSI/GitOps avec la version Kubernetes cible.
4. Faire un snapshot/backup etcd si cluster critique:
   - Talos: privilégier la procédure officielle Talos pour backups etcd.
5. Prévoir un rollback réaliste:
   - images Talos précédentes disponibles;
   - manifests GitOps inchangés ou branch/tag de rollback;
   - accès console/IPMI/physique si homelab.

### GitOps hardening rapide

1. Ne jamais committer de kubeconfig, talosconfig, tokens, `auth.json`, clés privées, secrets SOPS non chiffrés.
2. Ajouter/valider des règles pre-commit:
   - détection secrets type `gitleaks` ou équivalent;
   - lint YAML/Kubernetes manifests;
   - validation de `kustomize build` ou `helm template`.
3. Séparer les droits:
   - compte GitOps limité aux namespaces nécessaires;
   - éviter `cluster-admin` permanent pour le contrôleur GitOps hors besoin explicite.
4. Protéger les branches de prod:
   - PR obligatoire;
   - CI verte obligatoire;
   - pas de force-push.
5. Pour Flux/Argo:
   - activer le drift/health monitoring;
   - surveiller les réconciliations bloquées;
   - alerter sur les échecs prolongés plutôt que seulement sur le CPU/mémoire.

### Mini-exercice CKA lié

Objectif: s’entraîner aux probes, rollout et rollback.

```bash
kubectl create deployment web --image=nginx:1.27 --replicas=2
kubectl set image deployment/web nginx=nginx:1.28
kubectl rollout status deployment/web
kubectl rollout history deployment/web
kubectl rollout undo deployment/web
kubectl get deploy,rs,pods -l app=web
kubectl delete deployment web
```

Variante sécurité: ajouter un `securityContext` non-root et vérifier que le pod démarre encore.

## Prochaines actions utiles

1. Si Tom utilise Flux: comparer la version locale à `v2.8.8`, puis lire la procédure upgrade v2.7+ avant changement.
2. Si Tom utilise Argo CD: vérifier si la branche locale est `3.2`, `3.3` ou `3.4`, puis lire les notes d’upgrade correspondantes.
3. Si Talos est utilisé: planifier une fenêtre d’upgrade non urgente vers une release stable compatible, en évitant les alphas.
4. Ajouter un check `gitleaks`/lint manifest dans la CI GitOps si absent.
5. Créer une note d’inventaire homelab: nodes, rôles, IPs, stockage, CNI, CSI, GitOps controller, sauvegardes.
