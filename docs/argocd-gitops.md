# Argo CD GitOps with Ansible Bootstrap

## Goal

- Keep Ansible for cluster/bootstrap tasks (prereqs, MetalLB, Argo CD).
- Use Argo CD to deploy and continuously reconcile Kubernetes applications.

## Current behavior

`ansible/roles/kubernetes/tasks/main.yml` always runs:

1. prerequisites (`prereqs.yml`)
2. MetalLB (`metallb.yml`)
3. Argo CD (`argocd.yml`)

Then behavior depends on `kubernetes_deploy_mode`:

- `gitops` (default): configure Argo CD repo credentials and apply root app bootstrap
- `legacy`: deploy apps directly from Ansible role task files

## GitOps app source

- Repo URL: `argocd_gitops_repo_url`
- Revision: `argocd_gitops_repo_revision`
- Applications path: `argocd_gitops_apps_path` (default `kubernetes/argocd/apps`)

Defined Argo CD Applications:

- `traefik`, `blocky`, `homepage`, `keel`, `prometheus`, `grafana`,
  `navidrome`, `vaultwarden`, `trilium`, `forgejo`, `media`, `newt`,
  `stirling-pdf`, `ollama`, `openwebui`
- `actions-runner-controller-crds`, `actions-runner-controller`,
  `github-runners-auth`, `github-runners-dotfiles`, `github-runners-portfolio`,
  `github-runners-sumfeet`, `forgejo-runner-homelab`

## Sync-wave order

From `kubernetes/argocd/apps/*.yaml`:

- wave `0`: `traefik`
- wave `1`: `blocky`
- wave `2`: `homepage`, `keel`, `prometheus`
- wave `3`: `grafana`, `navidrome`, `vaultwarden`, `trilium`
- wave `4`: `forgejo`, `media`, `newt`, `stirling-pdf`, `ollama`
- wave `4`: `actions-runner-controller-crds`
- wave `5`: `openwebui`
- wave `5`: `actions-runner-controller`
- wave `6`: `forgejo-runner-homelab`, `github-runners-auth`
- wave `8`: `github-runners-portfolio`, `github-runners-dotfiles`,
  `github-runners-sumfeet`

## Important Ansible variables

Defaults are in `ansible/roles/kubernetes/defaults/main.yml`:

- `kubernetes_deploy_mode`
- `argocd_gitops_repo_url`
- `argocd_gitops_repo_revision`
- `argocd_gitops_apps_path`
- `argocd_gitops_repo_ssh_private_key`
- `argocd_gitops_repo_insecure_ignore_host_key`

## SSH repository access

If Argo CD tracks a private SSH repository (default URL points
to internal Forgejo), set `argocd_gitops_repo_ssh_private_key`.

When provided, Ansible creates the Argo CD repository Secret automatically.

Recommendation: store private key material with Ansible Vault.

## Commands

From `ansible/`:

```bash
./run.sh playbooks/deploy-apps.yml
```

Force GitOps mode explicitly:

```bash
./run.sh playbooks/deploy-apps.yml -e kubernetes_deploy_mode=gitops
```

Use legacy mode:

```bash
./run.sh playbooks/deploy-apps.yml -e kubernetes_deploy_mode=legacy
```

## Operational notes

- In GitOps mode, treat Git as the source of truth for app resources.
- Avoid changing the same resources through both direct `kubectl` and Argo CD.
- Keep secrets out of plaintext manifests whenever possible.
