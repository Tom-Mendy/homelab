# Homelab Infrastructure

This repository contains the infrastructure automation and configuration for my homelab setup.

## Structure

- **ansible/**: Ansible playbooks and configuration for server management
  - `install_kubernetes.sh`: Script to install Kubernetes cluster using Kubespray
  - `update.sh`: Script to update all servers
  - `playbook.yml`: Main Ansible playbook
  - `inventory/`: Server inventory configuration
  - `roles/`: Ansible roles for system configuration

- **homepage/**: Homepage dashboard configuration
  - `services.yaml`: Service definitions for the homepage dashboard

- **navidrome/**: Music streaming server configuration
  - `update.py`: Python script to sync Spotify playlists
  - `playlist.nsp`: Navidrome smart playlist configuration

## Quick Start

### Prerequisites
- Docker and Docker Compose
- SSH access to target servers
- SSH private key in `ansible/private_key`

### Deploy Kubernetes Cluster
```bash
cd ansible
chmod +x install_kubernetes.sh
./install_kubernetes.sh
```

### Update All Servers
```bash
cd ansible
./update.sh
```

### Sync Music Playlists
```bash
cd navidrome
python3 update.py
```

## Services

The homelab runs the following services:
- **Home Assistant** (192.168.1.11:8123) - Home automation
- **Blocky** (192.168.1.19:4000) - DNS ad blocker
- **Stirling PDF** (192.168.1.13:8080) - PDF editor
- **Excalidraw** (192.168.1.12:3000) - Drawing tool
- **Navidrome** (192.168.1.18:4533) - Music streaming
- **Synology NAS** (192.168.1.1:5001) - Network storage