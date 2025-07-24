# Homelab Network Diagram

## Overview
This document describes the network topology and infrastructure of the homelab environment.

## Network Configuration

### Node Details
| Node | IP Address | Roles | User | OS |
|------|------------|-------|------|----|
| node-1 | 192.168.1.11 | Control Plane, etcd, Worker | tmendy | Ubuntu Server |
| node-2 | 192.168.1.12 | Control Plane, etcd, Worker | tmendy | Ubuntu Server |
| node-3 | 192.168.1.13 | etcd, Worker | tmendy | Ubuntu Server |

## Network Topology

```mermaid
graph TB
    subgraph "Homelab Network (192.168.1.0/24)"
        subgraph "Kubernetes Cluster"
            node1["node-1<br/>192.168.1.11<br/>Control Plane + etcd + Worker"]
            node2["node-2<br/>192.168.1.12<br/>Control Plane + etcd + Worker"]
            node3["node-3<br/>192.168.1.13<br/>etcd + Worker"]
        end

        subgraph "Control Plane (HA)"
            cp1["Control Plane Instance 1<br/>(node-1)"]
            cp2["Control Plane Instance 2<br/>(node-2)"]
        end

        subgraph "etcd Cluster"
            etcd1["etcd Instance 1<br/>(node-1)"]
            etcd2["etcd Instance 2<br/>(node-2)"]
            etcd3["etcd Instance 3<br/>(node-3)"]
        end

        subgraph "Worker Nodes"
            worker1["Worker 1<br/>(node-1)"]
            worker2["Worker 2<br/>(node-2)"]
            worker3["Worker 3<br/>(node-3)"]
        end
    end

    %% Connections
    node1 -.-> cp1
    node2 -.-> cp2
    node1 -.-> etcd1
    node2 -.-> etcd2
    node3 -.-> etcd3
    node1 -.-> worker1
    node2 -.-> worker2
    node3 -.-> worker3

    %% etcd cluster communication
    etcd1 <--> etcd2
    etcd2 <--> etcd3
    etcd3 <--> etcd1

    %% Control plane HA
    cp1 <--> cp2

    %% Style
    classDef controlPlane fill:#e1f5fe
    classDef etcdNode fill:#f3e5f5
    classDef workerNode fill:#e8f5e8
    classDef physicalNode fill:#fff3e0,stroke:#ff9800,stroke-width:2px

    class cp1,cp2 controlPlane
    class etcd1,etcd2,etcd3 etcdNode
    class worker1,worker2,worker3 workerNode
    class node1,node2,node3 physicalNode
```

## Infrastructure Details

### Kubernetes Cluster Architecture
- **High Availability Control Plane**: 2 control plane nodes (node-1, node-2)
- **etcd Cluster**: 3-node etcd cluster for high availability
- **Worker Nodes**: All 3 nodes serve as worker nodes

### Network Specifications
- **Network Range**: 192.168.1.0/24
- **SSH User**: tmendy (with sudo privileges)
- **Management**: Ansible-managed infrastructure

### Node Functions

#### node-1 (192.168.1.11)
- Kubernetes Control Plane
- etcd cluster member
- Worker node

#### node-2 (192.168.1.12)
- Kubernetes Control Plane (HA pair with node-1)
- etcd cluster member
- Worker node

#### node-3 (192.168.1.13)
- etcd cluster member
- Worker node only

## Ansible Management
All nodes are managed through Ansible with the following groups:
- `kube_control_plane`: node-1, node-2
- `etcd`: node-1, node-2, node-3
- `kube_node`: node-1, node-2, node-3
- `k8s_cluster`: All nodes in the cluster
