# Restore qBittorrent With a Resilient NymVPN Sidecar

## Problem

qBittorrent was unavailable because its NymVPN restartable init container was
crash-looping. NymVPN treated the upstream account state `SYNCING_STATE` as a
fatal tunnel error, and all qBittorrent startup and readiness checks required a
connected tunnel. This made the WebUI unavailable even though blocking Internet
egress was the safe and desired failure mode.

The required outcome was to keep NymVPN, keep its kill switch, and adopt the
same operational model as the existing Gluetun deployment: the application is
available on the cluster LAN while the VPN sidecar owns Internet egress and
reconnects independently.

## Investigation and reasoning

The first sandboxed cluster query could not reach the Kubernetes API. Repeating
the read-only query with cluster-network permission exposed the real failure:

<!-- rumdl-disable MD013 -->

```text
Unable to connect to the server: dial tcp 10.0.0.21:6443: socket: operation not permitted

kubectl -n media logs deploy/qbittorrent -c nymvpn --tail=160
Error state: Internal("Account API failure: SYNCING_STATE ...")
Error: Tunnel entered error state Internal("Account API failure: SYNCING_STATE ...")
```

<!-- rumdl-enable MD013 -->

The Nym state PVC is separate from qBittorrent configuration and downloads. It
was therefore safe to reset only `qbittorrent-nymvpn-pvc` after scaling the
Deployment to zero. The existing access code registered successfully afterward,
but the account remained `Syncing`; stale local state was not the root cause.

The durable fix was implemented in the existing sidecar instead of introducing
another controller or VPN abstraction:

- upgrade the official Nym core binaries from `2026.10.0` to `2026.11.0`;
- initialize the daemon, LAN bypass route, country gateways, and kill switch;
- let qBittorrent start after daemon initialization, not tunnel connection;
- keep attempting recovery in the sidecar process;
- probe daemon initialization for startup, readiness, and liveness;
- preserve the explicit cluster pod route through `eth0` so Traefik remains
  reachable without allowing direct Internet egress.

Nym's official support documentation associates `SYNCING_STATE` with possible
clock drift. The worker clock was checked directly before ruling that out.

## Commands and results

### Reset only Nym client state

```text
kubectl -n media scale deployment/qbittorrent --replicas=0
deployment.apps/qbittorrent scaled

kubectl -n media wait --for=delete pod/qbittorrent-7bb89fb4b8-frxm4 --timeout=120s
pod/qbittorrent-7bb89fb4b8-frxm4 condition met

kubectl -n media get secret nymvpn-credentials ...
NYM_ACCESS_CODE present
```

A temporary pod mounted only `qbittorrent-nymvpn-pvc` and removed the contents
of its `config/` and `state/` directories. It did not mount the qBittorrent or
media claims.

```text
pod/qbittorrent-nymvpn-state-reset created
pod/qbittorrent-nymvpn-state-reset condition met
NymVPN state reset complete
pod "qbittorrent-nymvpn-state-reset" deleted from media namespace
```

The existing credential was accepted, but synchronization still did not finish:

```text
Your account has been set. Welcome to the Nym VPN!
State: Connecting wg, awaiting account readiness, try #0
Account state: Syncing
```

### Build, test, and publish the sidecar

The image was built from the official Nym `2026.11.0` release and checked before
publication:

```text
sh -n kubernetes/media/nymvpn/entrypoint.sh
sh kubernetes/media/nymvpn/entrypoint.sh self-test
exit code: 0

docker run --rm --entrypoint nym-vpnc nymvpn-sidecar:2026.11.0-1 --version
2026.11.0
```

The first Forgejo registry push failed after authentication because several blob
uploads returned HTTP 500 from the NFS-backed registry. A bounded three-attempt
retry was added to the existing workflow. The following publication succeeded:

```text
docker pull forgejo.tom-mendy.com/tom-mendy/nymvpn-sidecar:2026.11.0-1
Digest: sha256:1f2f1c045b35c5276f09f525b007f05e2469a88450586f871500f6d4257ca6a5
Status: Image is up to date
```

### Deploy through Flux

```text
flux reconcile source git flux-system --namespace flux-system
fetched revision refs/heads/main@sha1:1212b7e007527fe774bb302b9e047d441e8622ff

flux reconcile helmrelease media --namespace flux-system --with-source
applied revision 0.1.0+1212b7e00752

kubectl -n media get pod -l app=qbittorrent
qbittorrent-54d64cffc9-zfttx   2/2   Running   0   ...
```

An older Helm upgrade was already waiting on the previous connection-dependent
probe. Suspending and resuming the HelmRelease did not cancel that in-flight
action, so it was allowed to time out cleanly. Kubernetes also retained the old
readiness probe when it was initially omitted from the new template. Making the
probe explicit and daemon-based fixed the live Deployment and the Git source.
One first patch attempt exposed a shell-quoting mistake before the corrected
command succeeded:

```text
zsh:1: no matches found: -p=[op:replace]
deployment.apps/qbittorrent patched
deployment "qbittorrent" successfully rolled out
```

### Validate availability and the kill switch

Both the local WebUI and the path from Traefik returned HTTP 200:

```text
kubectl -n media exec deploy/qbittorrent -c qbittorrent -- \
  wget -qSO- --timeout=5 http://127.0.0.1:8080/ -O /dev/null
HTTP/1.1 200 OK

kubectl -n traefik exec deploy/traefik -- \
  wget -qSO- --timeout=5 http://qbittorrent.media.svc.cluster.local:8080/ -O /dev/null
HTTP/1.1 200 OK

curl --resolve qbittorrent.home.tom-mendy.com:443:10.0.0.60 \
  https://qbittorrent.home.tom-mendy.com/
200
```

The account was still synchronizing, while the egress test failed closed:

```text
nym-vpnc status
State: Connecting wg, awaiting account readiness, try #0

nym-vpnc account get
Account mode: Some(Api)
Account state: Syncing

wget -qO- --timeout=10 https://api.ipify.org
wget: bad address 'api.ipify.org'
command terminated with exit code 1
```

The selected gateways and cluster route remained correct:

```text
Entry point: Country { two_letter_iso_country_code: "FR" }
Exit point: Country { two_letter_iso_country_code: "CH" }
10.233.64.0/18 via 169.254.1.1 dev eth0
```

The official clock-drift recovery condition was not present, and an explicit
reconnect did not change the upstream account state:

```text
ssh tmendy@10.0.0.23 timedatectl status
System clock synchronized: yes
NTP service: active

nym-vpnc reconnect
nym-vpnc status
State: Connecting wg, awaiting account readiness, try #0
```

### Validate storage and scheduling

```text
./scripts/check-storage-policy.sh
storage policy ok

./scripts/test-helm-chart.sh
All repository charts: OK

rumdl check --fix .
Issues: Found 136 issues in 17/121 files

rumdl check docs/activity_report/2026-08-17-restore-qbittorrent-with-nymvpn.md
Success: No issues found in 1 file

kubectl -n media get pvc qbittorrent-nymvpn-pvc qbittorrent-config-pvc media-downloads-pvc
qbittorrent-nymvpn-pvc   Bound   nfs-k8s
qbittorrent-config-pvc  Bound   nfs-k8s
media-downloads-pvc     Bound   <static Synology NFS PV>

kubectl -n media get deployment qbittorrent ...
nodeSelector= affinity=
```

The repository-wide Markdown command remains non-zero because of 136 existing
issues in unrelated files. It made no unrelated changes, and this activity
report passes its focused check.

The Deployment has no worker affinity, and all persistent data is on shared
Synology NFS. It can therefore be rescheduled between `node2` and `node3`
without stranding data.

## Outcome

qBittorrent is restored as a `2/2 Running` workload and its WebUI is reachable
through Traefik even while Nym is unavailable. Internet egress remains blocked,
so there is no fallback to the worker's public connection and no ProtonVPN
dependency. Flux reports `UpgradeSucceeded` on revision `1212b7e`.

The Nym-specific Kubernetes implementation is complete and resilient, but the
current Nym account remains in the provider-side `Syncing` state. The client is
on the latest selected official release, its state was re-created, the daemon
was restarted, the worker clock is synchronized, and reconnect was attempted.
Until Nym's account API finishes synchronization, downloads correctly remain
blocked by the kill switch; resolving that remaining provider account state
requires Nym support rather than a Kubernetes bypass.
