# Media Stack Helm Chart

This directory is now a Helm chart, aligned with the pattern used
by the other charts in `kubernetes/`.

## Included apps

- `qBittorrent` (+ `NymVPN` sidecar)
- `NZBGet` (+ `Gluetun` sidecar)
- `Prowlarr`
- `Sonarr`
- `Radarr`
- `Bazarr`
- `Autobrr`

Only downloader apps are VPN-routed, ARR apps stay outside VPN. During the
NymVPN pilot, qBittorrent uses NymVPN while NZBGet keeps ProtonVPN as its
rollback path.

## Storage (NFS / NAS)

Configured in `values.yaml`:

- Downloads: `/volume1/Downloads`
- Movies: `/volume1/video/Film`
- Series: `/volume1/video/Serie`
- NFS server: `10.0.0.11`

Container identity defaults:

- `PUID=1023`
- `PGID=100`

## NymVPN pilot

The NymVPN sidecar image is built by `.forgejo/workflows/nymvpn-sidecar.yml`
and published as:

```text
forgejo.tom-mendy.com/tom-mendy/nymvpn-sidecar:2026.10.0-2
```

Configure these secrets in Infisical project `homelab`, environment `prod`,
path `/media`:

- `NYM_ACCESS_CODE`: the 24-word NymVPN access code.

The access code is mounted as a read-only file. NymVPN configuration and device
state are stored on `qbittorrent-nymvpn-pvc` with storage class `nfs-k8s`.
The pod uses the NymVPN DNS resolver on `127.0.0.1` and does not start
qBittorrent until the VPN startup probe succeeds. The sidecar keeps the cluster
pod CIDR routed through `eth0` so Traefik can reach the WebUI without bypassing
NymVPN for Internet traffic.

Before publishing the image, add the repository action secret
`REGISTRY_TOKEN`. It must be a Forgejo personal access token allowed to write
packages. The package is publicly pullable, so Kubernetes needs no registry
credential.

## ProtonVPN rollback credentials

For WireGuard, configure in `values.yaml`:

- `vpn.type=wireguard`
- `vpn.credentials.wireguardPrivateKey`

If you use OpenVPN instead, configure:

- `vpn.credentials.openvpnUser`
- `vpn.credentials.openvpnPassword`

For safer handling, set `vpn.createSecret=false` and provide a pre-created
secret named by `vpn.secretName`. In this repository, Infisical creates
`protonvpn-credentials` from project `homelab`, env `prod`, path `/media`.
Keep it until the qBittorrent pilot has run successfully for 48 hours and
NZBGet has also migrated to NymVPN.

## Local Helm test (optional)

```bash
helm template media ./kubernetes/media
```

Flux HelmRelease `media` points to this chart path and reconciles it
automatically.
