# Copilot Instructions - Homelab Infrastructure

## Architecture & Tech Stack
- **Infrastructure**: Managed with Ansible + Kubespray workflows.
- **Orchestration**: Kubernetes cluster managed from [ansible/](../ansible/), inventory in [ansible/inventory.ini](../ansible/inventory.ini).
- **GitOps**: Argo CD is the default deployment mode (`kubernetes_deploy_mode: gitops`) configured in [ansible/roles/kubernetes/defaults/main.yml](../ansible/roles/kubernetes/defaults/main.yml).
- **Ingress Controller**: Traefik.
- **LoadBalancer**: MetalLB.
- **DNS**: Blocky for `.home.tom-mendy.com` service resolution.
- **Naming Convention**: Internal services use `*.home.tom-mendy.com`.

## Critical Workflows
- **Ansible execution**:
  - Use [ansible/run.sh](../ansible/run.sh) as the single entry point; it manages `.venv`, Python deps, and Ansible collections.
  - Run playbooks from the `ansible/` directory.
  - SSH access relies on [ansible/private_key](../ansible/private_key).
- **Primary playbooks**:
  - Install cluster: [ansible/playbooks/install.yml](../ansible/playbooks/install.yml)
  - Deploy apps/platform: [ansible/playbooks/deploy-apps.yml](../ansible/playbooks/deploy-apps.yml)
  - Update nodes: [ansible/playbooks/update.yml](../ansible/playbooks/update.yml)
  - Reboot nodes: [ansible/playbooks/reboot.yml](../ansible/playbooks/reboot.yml)
  - Reset cluster: [ansible/playbooks/reset.yml](../ansible/playbooks/reset.yml)
- **Application deployment model**:
  - App definitions live under [kubernetes/](../kubernetes/).
  - GitOps applications are declared in [kubernetes/argocd/apps/](../kubernetes/argocd/apps/).
  - Additional manifests can exist outside Argo CD app declarations (for example `ollama` and `openwebui`).
- **Hardware integrations**:
  - NVIDIA runtime class lives at [kubernetes/ollama/runtimeclass-nvidia.yaml](../kubernetes/ollama/runtimeclass-nvidia.yaml).

## Project Patterns & Conventions
- **Ingress annotations**: Use `traefik.ingress.kubernetes.io/router.entrypoints: web, websecure` for Traefik-routed services.
- **DNS mapping**: Update `customDNS.mapping` in [kubernetes/blocky/config.yml](../kubernetes/blocky/config.yml) when adding internal hostnames.
- **Dashboard entries**: Add services to [kubernetes/homepage/services.yaml](../kubernetes/homepage/services.yaml).
- **GitOps onboarding**: For GitOps-managed services, add an Application manifest in [kubernetes/argocd/apps/](../kubernetes/argocd/apps/).

## Data Storage Policy
- **NAS usage**: Keep only content/media data on NAS; keep application state/config data on cluster-local storage unless explicitly documented otherwise.

## Current Repository Layout
- [.github/](../.github/): Repository automation and Copilot instructions.
- [ansible/](../ansible/): Cluster lifecycle, inventory, roles, playbooks, and runner script.
- [kubernetes/](../kubernetes/): Helm charts/manifests, Argo CD applications, and platform service configs.
- [docs/](../docs/): Operational runbooks and architecture/network documentation.
- [navidrome/](../navidrome/): Local utility scripts.
