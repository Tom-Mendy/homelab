# Migrate Worker Node IPs

## Problem

The homelab network migration moved worker nodes from `192.168.1.0/24` to
`10.0.0.0/24`. Kubernetes still reported the old node IPs until kubelet was
updated on each migrated worker.

## Reasoning and commands

`node3` was first moved to `10.0.0.23`. Kubelet initially failed because it was
still configured to bind the old address:

```text
Failed to listen and serve:
listen tcp 192.168.1.13:10250: bind: cannot assign requested address
```

The fix was to update the Kubespray-managed kubelet files on the node:

```sh
sudo sed -i 's/192\.168\.1\.13/10.0.0.23/g' \
  /etc/kubernetes/kubelet-config.yaml \
  /etc/kubernetes/kubelet.env
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

`node2` was then moved to `10.0.0.22` and fixed the same way:

```sh
sudo sed -i 's/192\.168\.1\.12/10.0.0.22/g' \
  /etc/kubernetes/kubelet-config.yaml \
  /etc/kubernetes/kubelet.env
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

Static host-network pods were checked after each node update. `nginx-proxy-node2`
needed its stale container stopped so kubelet could recreate it with the new
node IP.

## Results

Final node state after the worker migration:

```text
node1   Ready   control-plane   192.168.1.11
node2   Ready   <none>          10.0.0.22
node3   Ready   <none>          10.0.0.23
```

NFS was kept temporarily reachable at `192.168.1.1` because existing
PersistentVolumes still reference that immutable server field. The NAS also
allows `10.0.0.0/24`, so a later maintenance window can recreate PVs against
`10.0.0.11`.

## Outcome

Worker nodes now run on the new network. `node1` remains on `192.168.1.11` and
must be migrated last because it is the single control-plane node.
