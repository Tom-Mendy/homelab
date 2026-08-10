# Homelab Network Diagram

## Overview

This document describes the network topology and infrastructure of the homelab environment.

## Network Configuration

### Node Details

| Node | IP Address | Roles | User | OS |
|------|------------|-------|------|----|
| node1 | 10.0.0.21 | Control Plane, etcd | tmendy | Ubuntu Server |
| node2 | 10.0.0.22 | Worker | tmendy | Ubuntu Server |
| node3 | 10.0.0.23 | Worker (GPU label) | tmendy | Ubuntu Server |

## Network Topology

```mermaid
graph TB
    subgraph "Homelab Network (10.0.0.0/24)"
        subgraph "Kubernetes Cluster"
            node1["node1<br/>10.0.0.21<br/>Control Plane + etcd"]
            node2["node2<br/>10.0.0.22<br/>Worker"]
            node3["node3<br/>10.0.0.23<br/>Worker + GPU label"]
        end

        subgraph "Ingress & DNS"
            traefik["Traefik Ingress\n(MetalLB IP 10.0.0.60)"]
            blocky["Blocky DNS\nLoadBalancer 10.0.0.61"]
        end

        subgraph "GitOps Control"
            flux["Flux Operator + Flux\nflux-system"]
        end

        subgraph "Worker Nodes"
            worker2["Worker<br/>(node2)"]
            worker3["Worker<br/>(node3)"]
        end
    end

    node1 --> traefik
    node1 --> blocky
    node1 --> flux
    node2 --> traefik
    node3 --> traefik
    blocky --> traefik
    flux --> traefik

    %% Style
    classDef controlPlane fill:#e1f5fe
    classDef workerNode fill:#e8f5e8
    classDef platform fill:#f3e5f5
    classDef physicalNode fill:#fff3e0,stroke:#ff9800,stroke-width:2px

    class node1 controlPlane
    class worker2,worker3 workerNode
    class traefik,blocky,flux platform
    class node1,node2,node3 physicalNode
```

## Infrastructure Details

### Kubernetes Cluster Architecture

- **Control Plane**: single node (`node1`)
- **etcd**: collocated with control-plane node
- **Worker Nodes**: `node2`, `node3`

### Network Specifications

- **Network Range**: 10.0.0.0/24
- **LoadBalancer Range**: 10.0.0.60-10.0.0.89
- **SSH User**: tmendy (with sudo privileges)
- **Management**: Kubernetes plus Flux GitOps

### Node Functions

#### node1 (10.0.0.21)

- Kubernetes Control Plane
- etcd member

#### node2 (10.0.0.22)

- Worker node

#### node3 (10.0.0.23)

- Worker node
- Labeled `gpu=true` for GPU workloads

## GitOps Management

Flux Operator and the Flux controllers run in `flux-system`. They reconcile the
application charts from the in-cluster Forgejo repository.
