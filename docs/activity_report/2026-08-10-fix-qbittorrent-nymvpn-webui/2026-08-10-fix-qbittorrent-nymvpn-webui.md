# Fix qBittorrent WebUI routing through NymVPN

## Problem

`https://qbittorrent.home.tom-mendy.com` returned `Gateway Timeout`. The
qBittorrent pod was healthy, its WebUI answered on localhost, and its Service
had a ready endpoint, but Traefik could not reach port 8080.

## Investigation and reasoning

The failing and successful paths were compared:

```text
kubectl -n media exec deploy/qbittorrent -c qbittorrent -- \
  wget -qSO- --timeout=5 http://127.0.0.1:8080/
HTTP/1.1 200 OK

kubectl -n traefik exec deploy/traefik -- \
  wget -qSO- --timeout=5 http://qbittorrent.media.svc.cluster.local:8080/
wget: download timed out
```

Other media Services answered from Traefik, which isolated the fault to the
NymVPN network namespace. The former Gluetun deployment explicitly allowed
the WebUI port with `FIREWALL_INPUT_PORTS=8080`. NymVPN only used `lan set
allow` and did not preserve a route to the Kubernetes pod network.

The cluster ranges were read from the control plane:

```text
--cluster-cidr=10.233.64.0/18
--service-cluster-ip-range=10.233.0.0/18
```

A host-network proxy was tested and rejected. Although a disposable
host-network curl pod could reach qBittorrent, Traefik could not reach the
host-network proxy endpoints through a ClusterIP Service. The temporary
DaemonSet, Service, and ConfigMap were deleted and the original Ingress was
restored.

## Changes

The NymVPN image now contains `iproute2`. Before connecting, its entrypoint
records the default LAN gateway and interface. After every connection or
reconnection it installs an idempotent route for `10.233.64.0/18` through
that interface. The readiness check also verifies that this route exists.

The pod CIDR is supplied by the Helm value `nymVpn.podCidr`, and the image tag
was advanced to `2026.10.0-2` so nodes cannot reuse the previous image.

## Validation results

```text
sh -n kubernetes/media/nymvpn/entrypoint.sh
success

./scripts/test-helm-chart.sh
all 23 charts: OK

./scripts/check-storage-policy.sh
storage policy ok

docker build --tag nymvpn-sidecar:test kubernetes/media/nymvpn
success

docker run --rm --cap-add NET_ADMIN ... route self-check
success
```

After Forgejo published `nymvpn-sidecar:2026.10.0-2`, the first pod remained
temporarily in `ImagePullBackOff`. Its events still contained the earlier
registry response:

```text
Failed to pull image ... nymvpn-sidecar:2026.10.0-2: not found
```

No pod was deleted. The kubelet retried automatically and the pod became
ready. The live validation then produced:

```text
kubectl -n media rollout status deployment/qbittorrent --timeout=120s
deployment "qbittorrent" successfully rolled out

kubectl -n media exec deploy/qbittorrent -c nymvpn -- \
  ip -4 route show 10.233.64.0/18
10.233.64.0/18 via 169.254.1.1 dev eth0

kubectl -n traefik exec deploy/traefik -- \
  wget -qSO- http://qbittorrent.media.svc.cluster.local:8080/
HTTP/1.1 200 OK

curl --resolve qbittorrent.home.tom-mendy.com:443:10.0.0.60 \
  https://qbittorrent.home.tom-mendy.com/
HTTP 200

kubectl -n media exec deploy/qbittorrent -c qbittorrent -- \
  /app/qbittorrent-nox --version
qBittorrent v5.2.2
```

The HelmRelease had reached `Stalled` during the missing-image retries. The
local `flux` command was unavailable, so the first reconciliation command
failed with `flux: command not found`. A normal reconciliation annotation was
handled but could not clear `Stalled`. Renewing both `requestedAt` and
`forceAt` started one controlled retry. Its final result was:

```text
Ready=True | UpgradeSucceeded
Helm upgrade succeeded for release media/media.v7
1 updated / 1 ready / 1 total
```

The unauthenticated local Web API version request returned `403 Forbidden`,
so the running binary was queried directly instead. The final storage policy
check also returned `storage policy ok`.
