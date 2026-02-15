# Media Stack Helm Chart

This directory is now a Helm chart, aligned with the pattern used by the other charts in `kubernetes/`.

## Included apps

- `qBittorrent` (+ `Gluetun` sidecar)
- `NZBGet` (+ `Gluetun` sidecar)
- `Prowlarr`
- `Sonarr`
- `Radarr`
- `Bazarr`
- `Autobrr`

Only downloader apps are VPN-routed, ARR apps stay outside VPN.

## Storage (NFS / NAS)

Configured in `values.yaml`:

- Downloads: `/volume1/Downloads`
- Movies: `/volume1/video/Film`
- Series: `/volume1/video/Serie`
- NFS server: `192.168.1.1`

Container identity defaults:

- `PUID=1023`
- `PGID=100`

## ProtonVPN credentials

For WireGuard, configure in `values.yaml`:

- `vpn.type=wireguard`
- `vpn.credentials.wireguardPrivateKey`

If you use OpenVPN instead, configure:

- `vpn.credentials.openvpnUser`
- `vpn.credentials.openvpnPassword`

For safer handling, set `vpn.createSecret=false` and provide a pre-created secret named by `vpn.secretName`.

## Local Helm test (optional)

```bash
helm template media ./kubernetes/media
```

Argo CD app `kubernetes/argocd/apps/media.yaml` points to this chart path and will sync it automatically.
