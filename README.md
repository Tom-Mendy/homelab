# Homelab Infrastructure

Kubernetes homelab managed with Ansible + Kubespray, with Argo CD GitOps for app reconciliation.

## What is in this repo

- Cluster lifecycle automation in `ansible/`
- Kubernetes apps and manifests in `kubernetes/`
- Operational runbooks in `docs/`
- Homepage dashboard configuration in `kubernetes/homepage/services.yaml`

## Current architecture

- **Nodes**: `node1` (`192.168.1.11`), `node2` (`192.168.1.12`), `node3` (`192.168.1.13`)
- **Control plane**: `node1`
- **Workers**: `node2`, `node3`
- **Ingress**: Traefik
- **LoadBalancer IPs**: MetalLB (`192.168.1.20-192.168.1.49`)
- **DNS**: Blocky (`blocky` service exposed at `192.168.1.21`)
- **Domain convention**: `*.home.tom-mendy.com`

## Deployed services

### GitOps-managed (Argo CD Applications)

- `traefik`
- `blocky`
- `homepage`
- `keel`
- `prometheus`
- `grafana`
- `navidrome`
- `vaultwarden`
- `forgejo`
- `trilium`
- `media`
- `newt`
- `stirling-pdf`
- `ollama`
- `openwebui`
- `searxng`
- `actions-runner-controller`
- `actions-runner-controller-crds`
- `github-runners`
- `github-runners-capstone2`
- `github-runners-portfolio`

## Quick start

### 1) Prepare access

1. Clone repository:

 ```bash
 git clone https://github.com/Tom-Mendy/homelab.git
 cd homelab
 ```

2. Place SSH key for Ansible at `ansible/private_key`.
3. Review `ansible/inventory.ini`.

### 2) Install cluster (first bootstrap)

```bash
cd ansible
./run.sh playbooks/install.yml
```

### 3) Deploy platform + apps

```bash
cd ansible
./run.sh playbooks/deploy-apps.yml
```

## Ansible playbooks

From `ansible/`:

- Install base + Kubernetes: `./run.sh playbooks/install.yml`
- Deploy apps/platform: `./run.sh playbooks/deploy-apps.yml`
- OS update tasks: `./run.sh playbooks/update.yml`
- Reboot all nodes: `./run.sh playbooks/reboot.yml`
- Reset Kubernetes cluster: `./run.sh playbooks/reset.yml`

## Deployment mode

`ansible/roles/kubernetes/defaults/main.yml` defines:

- `kubernetes_deploy_mode=gitops` (default)
- `kubernetes_deploy_mode=legacy` (direct Ansible service deployment)

Override example:

```bash
cd ansible
./run.sh playbooks/deploy-apps.yml -e kubernetes_deploy_mode=legacy
```

## Service onboarding checklist

When adding a new internal service:

1. Add Kubernetes manifests/chart under `kubernetes/<service>/`
2. Add DNS mapping in `kubernetes/blocky/config.yml` (`customDNS.mapping`)
3. Add homepage entry in `kubernetes/homepage/services.yaml`
4. If GitOps-managed, add an Argo CD Application in `kubernetes/argocd/apps/`

## Repository layout (summary)

```text
homelab/
├── ansible/                 # Playbooks, inventory, roles, run.sh
├── docs/                    # Runbooks and architecture docs
├── kubernetes/              # App manifests/charts and GitOps apps
├── navidrome/               # Local utility script(s)
└── README.md
```

## Documentation index

- `docs/network-diagram.md`
- `docs/argocd-gitops.md`
- `docs/acme-dns01-private-services.md`
- `docs/backup-procedures.md`
- `docs/disaster-recovery.md`
- `kubernetes/kube-config-to-normal-user.md`
- `kubernetes/ollama/README.md`

![Keel dashboard](./docs/images/keel.png)
