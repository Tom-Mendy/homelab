# Migrate Synology NFS IP

## Problem

The homelab network migration moved the Synology NAS from `192.168.1.1` to
`10.0.0.11`. Kubernetes storage still referenced the old NAS IP in the NFS
provisioner and in static NFS PV chart values.

## Reasoning and commands

Before changing Kubernetes manifests, the NAS had to expose the same NFS shares
on the new subnet.

```sh
showmount -e 10.0.0.11
```

Result:

```text
Export list for 10.0.0.11:
/volume1/Downloads   10.0.0.0/24,192.168.1.0/24
/volume1/music       10.0.0.0/24,192.168.1.0/24
/volume1/prometheus  10.0.0.0/24,192.168.1.0/24
/volume1/video       10.0.0.0/24,192.168.1.0/24
/volume1/vaultwarden 10.0.0.0/24,192.168.1.0/24
/volume1/forgejo     10.0.0.0/24,192.168.1.0/24
/volume1/k8s         10.0.0.0/24,192.168.1.0/24
```

This confirmed that both the dynamic `nfs-k8s` backing export and the fixed
media/application exports are available from `10.0.0.0/24`.

## Changes

Updated active NFS references from `192.168.1.1` to `10.0.0.11` for:

- `nfs-k8s` provisioner backing server.
- Static NFS PV chart values for media, Navidrome music, Prometheus,
  Vaultwarden, and Forgejo.
- Homepage Synology link and storage documentation.

Historical activity reports were left unchanged because they describe previous
states.

## Outcome

Kubernetes desired state now targets the Synology NAS at `10.0.0.11` while
keeping the same NFS exports and `nfs-k8s` storage policy.
