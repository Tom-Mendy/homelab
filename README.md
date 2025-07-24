# Homelab Infrastructure

A personal homelab setup for learning, experimentation, and self-hosting various services.

## Overview

This repository contains configuration files, documentation, and automation scripts for my homelab infrastructure. The goal is to create a reproducible, scalable, and well-documented environment for hosting various services and applications.

## Architecture

### Hardware
- **Main Server**: [Add your hardware specs here]
- **Network Equipment**: [Router, switches, etc.]
- **Storage**: [NAS, external drives, etc.]

### Software Stack
- **Operating System**: [Ubuntu Server]
- **Orchestration**: [Kubernetes]
- **Monitoring**: [Prometheus, Grafana, etc.]
- **Networking**: [Traefik, nginx, etc.]

## Services

### Core Services
- [ ] DNS Server (Blocky)
- [ ] Reverse Proxy (Traefik, nginx)
- [ ] Certificate Management (Let's Encrypt)
- [ ] Monitoring & Logging (Prometheus, Grafana, Loki, Promtail)
- [ ] Backup Solutions
- [ ] Authentication (Authelia, Keycloak)

### Applications
- [ ] Admin Panel (Portainer, Keel + admin dashboard)
- [ ] Document Storage (Paperless-gnx, Paperless-AI)
- [ ] Note App (Trilium)
- [ ] Container Registry (Harbort)
- [ ] Home Automation (Home Assistant)
- [ ] Remote Access (twingate)
- [ ] Git Runner Server (GitLab, Github)
- [ ] Pod Container (Gitpod)
- [ ] Password Manager (Vaultwarden)
- [ ] AI usage (Ollama, Ollama-WebUI)
- [ ] Database (PostgreSQL, CloudBeaver)
- [ ] Tools ([wol-web](https://github.com/HuakunShen/wol-web), UpTimeKuma)


## Getting Started

### Prerequisites
- Linux server with Docker installed
- Domain name (optional, for external access)
- Basic understanding of Docker and networking

### Installation

1. Clone this repository:
```bash
git clone https://github.com/Tom-Mendy/homelab.git
cd homelab
```

2. Copy and customize environment files:
```bash
cd ansible
cp /path/to/ssh-key ./ansible/private_key
# Edit inventory.ini with your specific configuration
```


3. Start core services:
```bash
docker-compose up -d
```

### Configuration

#### Network Setup
- **Internal Network**: `192.168.1.0/24`
- **Docker Network**: `172.18.0.0/16`

#### DNS Configuration
Update your router's DNS settings to point to your Pi-hole instance for network-wide ad blocking.

## Directory Structure

```
homelab/
├── ansible/                   # Ansible playbooks and configs
│   ├── kubespray/             # Kubespray for K8s installation
│   ├── inventory/             # Host inventories
│   └── playbooks/             # Custom playbooks
├── kubernetes/                # Kubernetes manifests
│   ├── core/                  # Core services (DNS, proxy, certs)
│   │   ├── blocky/           # DNS server configs
│   │   ├── traefik/          # Reverse proxy
│   │   └── cert-manager/     # Certificate management
│   ├── monitoring/           # Monitoring stack
│   │   ├── prometheus/       # Metrics collection
│   │   ├── grafana/          # Dashboards
│   │   └── loki/             # Log aggregation
│   ├── auth/                 # Authentication services
│   │   ├── authelia/         # Auth middleware
│   │   └── keycloak/         # Identity provider
│   ├── apps/                 # Application deployments
│   │   ├── portainer/        # Container management
│   │   ├── paperless/        # Document storage
│   │   ├── trilium/          # Note-taking
│   │   ├── vaultwarden/      # Password manager
│   │   ├── home-assistant/   # Home automation
│   │   └── ollama/           # AI services
│   └── storage/              # Storage configs
│       ├── postgresql/       # Database
│       └── persistent-volumes/
├── configs/                  # Configuration files
│   ├── .env.example         # Environment template
│   ├── hosts                # Host definitions
│   └── secrets/             # Secret templates
├── scripts/                 # Automation scripts
│   ├── backup.sh           # Backup automation
│   ├── update.sh           # Update procedures
│   └── deploy.sh           # Deployment scripts
├── docs/                    # Documentation
│   ├── network-diagram.md   # Network topology
│   ├── backup-procedures.md # Backup guides
│   └── disaster-recovery.md # Recovery procedures
├── monitoring/              # Monitoring configs
│   ├── alerts/             # Alert rules
│   └── dashboards/         # Grafana dashboards
├── backups/                # Backup configurations
│   └── policies/           # Backup policies
├── .gitignore              # Git ignore rules
├── LICENSE                 # License file
└── README.md               # This file
```

## Backup Strategy

### Automated Backups
- **Configuration**: Daily backup of all config files
- **Application Data**: Weekly full backups
- **Media**: Monthly incremental backups

### Backup Locations
- Local NAS
- Cloud storage (encrypted)
- Off-site location

## Security

### Best Practices
- [ ] Regular security updates
- [ ] Strong passwords and 2FA
- [ ] Firewall configuration
- [ ] VPN access for external connections
- [ ] Regular backup testing
- [ ] SSL/TLS encryption for all services

### Access Control
- Internal services accessible only via VPN
- Public services protected by authentication
- Regular audit of user access

## Monitoring

### Key Metrics
- System resources (CPU, RAM, Disk)
- Network traffic
- Service uptime
- Container health
- Storage usage

### Alerts
- Service downtime
- High resource usage
- Backup failures
- Security events

## Maintenance

### Regular Tasks
- [ ] Weekly: Check service status
- [ ] Monthly: Update containers
- [ ] Quarterly: Security audit
- [ ] Annually: Hardware health check

### Update Process
1. Review changelogs
2. Test in development environment
3. Create backup
4. Deploy updates
5. Verify functionality

## Troubleshooting

### Common Issues

#### Service won't start
```bash
# Check container logs
docker logs <container_name>

# Check system resources
htop
df -h
```

#### Network connectivity issues
```bash
# Test internal connectivity
ping <service_ip>

# Check DNS resolution
nslookup <domain>

# Verify firewall rules
sudo ufw status
```

## Documentation

- [Service-specific documentation](docs/)
- [Network diagram](docs/network-diagram.md)
- [Backup procedures](docs/backup-procedures.md)
- [Disaster recovery](docs/disaster-recovery.md)

## Contributing

This is a personal homelab project, but feel free to:
- Submit issues for bugs or suggestions
- Fork the repository for your own use
- Share improvements via pull requests

## Resources

### Useful Links
- [Awesome Selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted)
- [r/homelab](https://www.reddit.com/r/homelab/)
- [Docker Documentation](https://docs.docker.com/)
- [Homelab Wiki](https://github.com/khuedoan/homelab)

### Learning Resources
- [Docker Compose Tutorial](https://docs.docker.com/compose/gettingstarted/)
- [Linux System Administration](https://linuxjourney.com/)
- [Networking Fundamentals](https://www.cisco.com/c/en/us/solutions/small-business/resource-center/networking/networking-basics.html)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### [1.0.0] - 2025-07-24
- Initial homelab setup
- Kubernetes installation via ansible (kubespray)
- Documentation creation

---
