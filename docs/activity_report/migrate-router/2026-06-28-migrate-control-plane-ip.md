# Migrate the Kubernetes Control Plane IP

## Problem

The homelab LAN is being migrated from `192.168.1.0/24` to `10.0.0.0/24`.
`node1` is the single control-plane and etcd node, so moving it from
`192.168.1.11` to `10.0.0.21` required updating etcd, the static API server
manifest, and kubelet node IP configuration.

## Reasoning and Commands

First, the new control-plane address was tested from the local machine:

```sh
kubectl --server=https://10.0.0.21:6443 --tls-server-name=node1 get nodes -o wide
```

The API certificate currently contains the DNS name `node1`, but not the IP
address `10.0.0.21`. For that reason, clients must either connect to a name
that resolves to `10.0.0.21`, or set `tls-server-name: node1` in the kubeconfig.

On `node1`, the control-plane migration required these effective changes:

```sh
sudo etcdctl member update <node1-member-id> --peer-urls=https://node1:2380
sudo sed -i 's/192\.168\.1\.11/10.0.0.21/g' \
  /etc/kubernetes/kubelet-config.yaml \
  /etc/kubernetes/kubelet.env \
  /etc/kubernetes/kubeadm-config.yaml
```

The etcd environment was changed to advertise `node1` and listen on
`10.0.0.21`:

```text
ETCD_ADVERTISE_CLIENT_URLS=https://node1:2379
ETCD_INITIAL_ADVERTISE_PEER_URLS=https://node1:2380
ETCD_LISTEN_CLIENT_URLS=https://10.0.0.21:2379,https://127.0.0.1:2379
ETCD_LISTEN_PEER_URLS=https://10.0.0.21:2380
ETCD_INITIAL_CLUSTER=etcd1=https://node1:2380
```

The API server static pod manifest was changed to advertise `10.0.0.21` and use
local etcd:

```text
--advertise-address=10.0.0.21
--etcd-servers=https://127.0.0.1:2379
```

The first restart left an old backup file in `/etc/kubernetes/manifests`.
Kubelet treats every YAML file in that directory as a static pod manifest, so it
kept recreating an old API server pod. The backup files were moved out of the
manifest directory before restarting kubelet again.

## Results

The API server became reachable on the new IP:

```sh
curl -k --connect-timeout 8 https://10.0.0.21:6443/readyz
```

Observed result:

```text
ok
```

The cluster saw the node IPs as migrated:

```text
NAME    STATUS     ROLES           INTERNAL-IP
node1   Ready      control-plane   10.0.0.21
node2   NotReady   <none>          10.0.0.22
node3   NotReady   <none>          10.0.0.23
```

`node2` and `node3` had valid OS networking and could reach the API server:

```sh
curl -kI --connect-timeout 5 https://10.0.0.21:6443
```

Observed result:

```text
HTTP/2 403
```

The `403` is expected for an unauthenticated request and proves network reachability.

## Outcome

`node1` now runs the control-plane on `10.0.0.21`. Repository inventory and
network documentation were updated for the new node IPs.

The remaining action is to update the worker kubelet kubeconfigs on `node2` and
`node3` so they stop posting to the old API endpoint `192.168.1.11`.

After updating the worker kubelet/API proxy configuration, all nodes reported
`Ready` on the new LAN:

```text
node1   Ready   control-plane   10.0.0.21
node2   Ready   <none>          10.0.0.22
node3   Ready   <none>          10.0.0.23
```

The worker-side files that needed correction were the kubelet kubeconfigs and
the Kubespray nginx API proxy configuration under `/etc/nginx`.
