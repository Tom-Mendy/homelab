# Media Stack Helm Chart

This directory is now a Helm chart, aligned with the pattern used
by the other charts in `kubernetes/`.

## Included apps

- `qBittorrent` (+ `NymVPN` sidecar)
- `NZBGet` (+ `NymVPN` sidecar)
- `Prowlarr`
- `Sonarr`
- `Radarr`
- `Bazarr`
- `Autobrr`

Only downloader apps are VPN-routed, ARR apps stay outside VPN. qBittorrent
and NZBGet use NymVPN.

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
forgejo.tom-mendy.com/tom-mendy/nymvpn-sidecar:2026.11.3-3
```

Configure these secrets in Infisical project `homelab`, environment `prod`,
path `/media`:

- `NYM_ACCESS_CODE`: the 24-word NymVPN access code.

The access code is mounted as a read-only file. NymVPN configuration and device
state are stored on separate PVCs for qBittorrent and NZBGet with storage class
`nfs-k8s`.
The pod uses the NymVPN DNS resolver on `127.0.0.1`. It starts the application
after the daemon, LAN policy, kill switch and connection request are
initialized. A VPN outage keeps the WebUI available while NymVPN blocks
Internet traffic and reconnects in the background. The sidecar keeps the
cluster pod CIDR routed through `eth0` so Traefik can reach the WebUI without
bypassing NymVPN for Internet traffic.
If a connection attempt remains non-Connected for 60 seconds, the sidecar
selects a different WireGuard exit gateway in the configured exit country and
retries indefinitely. The kill switch remains active during each rotation.

Before publishing the image, add the repository action secret
`REGISTRY_TOKEN`. It must be a Forgejo personal access token allowed to write
packages. The package is publicly pullable, so Kubernetes needs no registry
credential.

Infisical creates `nymvpn-credentials` from project `homelab`, environment
`prod`, path `/media`.

## Local Helm test (optional)

```bash
helm template media ./kubernetes/media
```

Flux HelmRelease `media` points to this chart path and reconciles it
automatically.
