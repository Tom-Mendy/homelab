# Copilot Instructions - Homelab Infrastructure

## Architecture & Tech Stack
- **Infrastructure**: Managed via Ansible using Kubespray.
- **Orchestration**: Kubernetes (K8s) cluster on multiple nodes (see [ansible/inventory.ini](../ansible/inventory.ini)).
- **Ingress Controller**: Traefik (configured via annotations on Ingress resources).
- **DNS**: Blocky handles local `.tom-mendy.local` resolution (defined in [kubernetes/blocky/blocky.yaml](../kubernetes/blocky/blocky.yaml)).
- **Naming Convention**: All internal services use `*.tom-mendy.local`.

## Critical Workflows
- **Ansible Management**:
  - Entry point is [ansible/run.sh](../ansible/run.sh), which manages a virtual environment and installs dependencies.
  - Playbooks live in [ansible/playbooks/](../ansible/playbooks/) and are executed from the `ansible/` directory.
  - SSH access relies on [ansible/private_key](../ansible/private_key).
- **Service Deployment**:
  - Services are organized in individual directories under [kubernetes/](../kubernetes/).
  - Deployment typically uses `helm` (for Keel, Ollama, Open WebUI) or raw manifests.
  - Check for `install.sh` in service folders for specific installation logic.
- **Hardware Integrations**:
  - NVIDIA GPU support via specialized runtime classes (see [kubernetes/ollama/runtimeclass-nvidia.yaml](../kubernetes/ollama/runtimeclass-nvidia.yaml)).
  - MetalLB handles LoadBalancer IP allocation.

## Project Patterns & Conventions
- **Ingresses**: Use the annotation `traefik.ingress.kubernetes.io/router.entrypoints: web`.
- **DNS Mapping**: When adding a new service, update the `customDNS` mapping in [kubernetes/blocky/blocky.yaml](../kubernetes/blocky/blocky.yaml).
- **Dashboard**: New services should be added to [homepage/services.yaml](../homepage/services.yaml) for appearing on the `homepage` dashboard.
- **Maintenance**: Use [ansible/playbooks/update.yml](../ansible/playbooks/update.yml) for cluster-wide updates and [ansible/playbooks/reboot.yml](../ansible/playbooks/reboot.yml) for managed reboots.

## Data Storage Policy
- **NAS Usage**: Store only content data on the NAS. Application data must remain on local cluster storage.

## Directory Structure
- [.github/](../.github/): Repository automation and Copilot instructions.
- [ansible/](../ansible/): Cluster lifecycle and node maintenance; includes [ansible/playbooks/](../ansible/playbooks/) and [ansible/inventory/](../ansible/inventory/).
- [kubernetes/](../kubernetes/): Application manifests and Helm chart configurations.
- [docs/](../docs/): Technical documentation and network diagrams.
- [homepage/](../homepage/): Dashboard configuration using `gethomepage.dev`.
- [navidrome/](../navidrome/): Local utility scripts and media playlist helpers.
