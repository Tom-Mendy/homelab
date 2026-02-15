# Migration vers Argo CD (GitOps) en conservant Ansible

## Objectif

- Conserver Ansible pour le **bootstrap cluster** (prérequis, MetalLB, Argo CD).
- Déléguer le déploiement et la réconciliation des applications Kubernetes à **Argo CD**.

## Ce qui a été mis en place

- Nouveau mode Ansible: `kubernetes_deploy_mode`
  - `gitops` (par défaut): bootstrap Argo CD + app racine GitOps
  - `legacy`: comportement historique (Ansible déploie chaque service)
- App racine Argo CD: `homelab-root`
  - source repo: `argocd_gitops_repo_url`
  - path: `kubernetes/argocd/apps`
- Applications Argo CD créées pour:
  - `traefik`, `blocky`, `homepage`, `keel`, `prometheus`, `grafana`, `navidrome`, `vaultwarden`, `forgejo`, `trilium`
- Ajout de charts Helm locaux pour gérer les manifests complémentaires:
  - `kubernetes/traefik`, `kubernetes/keel`, `kubernetes/prometheus`, `kubernetes/grafana`, `kubernetes/blocky`, `kubernetes/homepage`

## Variables Ansible utiles

Les valeurs par défaut sont dans `ansible/roles/kubernetes/defaults/main.yml`.

Variables principales:

- `kubernetes_deploy_mode`: `gitops` ou `legacy`
- `argocd_gitops_repo_url`: URL Git suivie par Argo CD
- `argocd_gitops_repo_revision`: branche/tag (ex: `main`)
- `argocd_gitops_apps_path`: chemin des `Application` Argo CD
- `argocd_gitops_repo_ssh_private_key`: clé privée SSH (si repo SSH)
- `argocd_gitops_repo_insecure_ignore_host_key`: `true`/`false`

## Repo Forgejo via SSH

Pour une URL SSH (ex: `ssh://git@forgejo.forgejo.svc.cluster.local/Tom-Mendy/homelab.git`), Argo CD a besoin d’une clé privée.

Le rôle Ansible crée automatiquement un Secret repository Argo CD (`argocd-repo-homelab`) **si** `argocd_gitops_repo_ssh_private_key` est renseignée.

Recommandation:

- stocker cette variable dans un fichier chiffré Ansible Vault.

## Exécution

Depuis `ansible/`:

```bash
./run.sh playbooks/deploy-apps.yml
```

Avec override temporaire:

```bash
./run.sh playbooks/deploy-apps.yml -e kubernetes_deploy_mode=gitops
```

Retour arrière (mode historique):

```bash
./run.sh playbooks/deploy-apps.yml -e kubernetes_deploy_mode=legacy
```

## Notes importantes

- Éviter d’utiliser Ansible et Argo CD en parallèle sur les mêmes ressources (hors mode `legacy`).
- Les changements applicatifs doivent passer par Git pour rester cohérents avec GitOps.
- Les manifests de secrets en clair sont à éviter; préférer Vault/SealedSecrets/SOPS à terme.
