# Homelab Network Diagram

## Overview

This document describes the network topology and infrastructure of the homelab environment.

## Network Configuration

### Node Details

| Node | IP Address | Roles | User | OS |
|------|------------|-------|------|----|
| node1 | 192.168.1.11 | Control Plane, etcd | tmendy | Ubuntu Server |
| node2 | 192.168.1.12 | Worker | tmendy | Ubuntu Server |
| node3 | 192.168.1.13 | Worker (GPU label) | tmendy | Ubuntu Server |

## Network Topology

```mermaid
graph TB
    subgraph "Homelab Network (192.168.1.0/24)"
        subgraph "Kubernetes Cluster"
            node1["node1<br/>192.168.1.11<br/>Control Plane + etcd"]
            node2["node2<br/>192.168.1.12<br/>Worker"]
            node3["node3<br/>192.168.1.13<br/>Worker + GPU label"]
        end

        subgraph "Ingress & DNS"
            traefik["Traefik Ingress\n(MetalLB IP range 192.168.1.20-49)"]
            blocky["Blocky DNS\nLoadBalancer 192.168.1.21"]
        end

        subgraph "GitOps Control"
            argocd["Argo CD\nargocd.home.tom-mendy.com"]
        end

        subgraph "Worker Nodes"
            worker2["Worker<br/>(node2)"]
            worker3["Worker<br/>(node3)"]
        end
    end

    node1 --> traefik
    node1 --> blocky
    node1 --> argocd
    node2 --> traefik
    node3 --> traefik
    blocky --> traefik
    argocd --> traefik

    %% Style
    classDef controlPlane fill:#e1f5fe
    classDef workerNode fill:#e8f5e8
    classDef platform fill:#f3e5f5
    classDef physicalNode fill:#fff3e0,stroke:#ff9800,stroke-width:2px

    class node1 controlPlane
    class worker2,worker3 workerNode
    class traefik,blocky,argocd platform
    class node1,node2,node3 physicalNode
```

## Infrastructure Details

### Kubernetes Cluster Architecture

- **Control Plane**: single node (`node1`)
- **etcd**: collocated with control-plane node
- **Worker Nodes**: `node2`, `node3`

### Network Specifications

- **Network Range**: 192.168.1.0/24
- **SSH User**: tmendy (with sudo privileges)
- **Management**: Ansible-managed infrastructure

### Node Functions

#### node1 (192.168.1.11)

- Kubernetes Control Plane
- etcd member

#### node2 (192.168.1.12)

- Worker node

#### node3 (192.168.1.13)

- Worker node
- Labeled `gpu=true` by Ansible prerequisites

## Ansible Management

All nodes are managed through Ansible with the following groups:

- `kube_control_plane`: `node1`
- `etcd`: `node1`
- `kube_node`: `node2`, `node3`
