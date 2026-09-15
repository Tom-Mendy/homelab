# Rotate NymVPN Exit Gateways After Failed Connections

## Problem

qBittorrent continued to show `External IP: N/A` because NymVPN stayed in a
non-connected state while using the same configured Swiss exit selection. The
safe behavior was already correct: the WebUI remained available and the kill
switch blocked Internet traffic. The missing behavior was automatic gateway
rotation.

## Investigation and reasoning

The running client exposes the official gateway commands:

```text
nym-vpnc gateway set --help
--exit-id <EXIT_ID>
--exit-country <EXIT_COUNTRY>
--exit-random

nym-vpnc gateway list-filtered --help
nym-vpnc gateway list-filtered wg --country CH --min-score medium
Filtered gateways available for: Wg (32)
```

The sidecar originally called `nym-vpnc connect` in the foreground. With the
newer client, that command can remain blocked while the state is `Connecting`,
so the 60-second loop could not run. The implementation therefore starts the
connect command in the background, tracks its PID, and stops it before changing
the exit gateway.

## Changes

- Upgraded the pinned official Nym binaries from `2026.11.0` to `2026.11.3`.
- Added a 60-second connection timer to the existing sidecar loop.
- Listed WireGuard gateways in the configured exit country and selected an
  `exit-id` different from the previous one.
- Rotated immediately on `Error` or `Disconnected`, and indefinitely until
  `Connected`.
- Preserved the LAN route, kill switch, and daemon-based probes.
- Logged only the selected gateway ID and rotation reason.

## Commands and results

```text
sh -n kubernetes/media/nymvpn/entrypoint.sh
exit code: 0

sh kubernetes/media/nymvpn/entrypoint.sh self-test
exit code: 0

helm lint kubernetes/media
1 chart(s) linted, 0 chart(s) failed

./scripts/check-storage-policy.sh
storage policy ok
```

The local image build verified both official checksums and the installed CLI:

```text
docker run --rm --entrypoint nym-vpnc nymvpn-sidecar:2026.11.3-1 --version
nym-vpnc 2026.11.3
```

Forgejo registry publication was slow because the registry stores blobs on NFS,
but the final image was pulled successfully:

```text
docker pull forgejo.tom-mendy.com/tom-mendy/nymvpn-sidecar:2026.11.3-3
Digest: sha256:30c2e85980e615dafc896b5e1d26c269fcf49012a13c904c0fff75c131b94562
```

Flux applied the chart successfully:

```text
flux reconcile helmrelease media --namespace flux-system --with-source
applied revision 0.1.0+27ca762d925e

kubectl -n media get pod -l app=qbittorrent
qbittorrent-867b749497-mvzjl   2/2   Running   0   ...
```

The live logs prove that different Swiss gateways are selected:

```text
rotating NymVPN exit gateway in CH (state)
selected NymVPN exit gateway: 2L7jtonY8fuXvfy2kytCA9uypkWxoSbxfqZVETMAWLYT
rotating NymVPN exit gateway in CH (state)
selected NymVPN exit gateway: 2BuMSfMW3zpeAjKXyKLhmY4QW1DXurrtSPEJ6CjX3SEh
rotating NymVPN exit gateway in CH (state)
selected NymVPN exit gateway: 2L7jtonY8fuXvfy2kytCA9uypkWxoSbxfqZVETMAWLYT
```

The qBittorrent WebUI remained healthy while NymVPN failed closed:

```text
HTTP/1.1 200 OK

wget -qO- --timeout=10 https://api.ipify.org
wget: bad address 'api.ipify.org'
command terminated with exit code 1
```

The remaining failure is provider account state, not a stuck gateway:

```text
nym-vpnc status
State: Error state: Internal("Account API failure: ZK_NYM_STATE ...")
```

## Outcome

The sidecar now automatically cycles through Swiss WireGuard gateways every 60
seconds when a connection does not succeed, while preserving the kill switch
and qBittorrent WebUI availability. Flux reports `UpgradeSucceeded`, storage
remains NFS-backed, and no ProtonVPN fallback was introduced.

The current Nym account still returns `ZK_NYM_STATE`; until Nym accepts the
account, `External IP` correctly remains unavailable and Internet traffic stays
blocked. Once the account is healthy, the same rotation loop will establish a
working Swiss exit without further Kubernetes changes.
