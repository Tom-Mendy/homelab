# Move Media VPN Secret to Infisical

## Problem

The media stack committed a ProtonVPN WireGuard private key in
`kubernetes/media/values.yaml`. The qbittorrent and nzbget VPN sidecars consume
the Kubernetes Secret `protonvpn-credentials` with key
`WIREGUARD_PRIVATE_KEY`, so that name and key must stay stable.

## Reasoning path

The media chart already supports `vpn.createSecret=false` and an externally
created Secret named by `vpn.secretName`. The migration disables literal Secret
rendering and adds Infisical v1beta1 resources that create
`protonvpn-credentials`.

The Kubernetes Auth machine identity is:

```text
name: media-k8s-auth
identityID: 69201a96-2f66-46ef-a4a2-1e81c08a3dfb
namespace: media
service account: media-infisical-sync
```

Infisical project `homelab`, env `prod`, path `/media` must contain:

```text
WIREGUARD_PRIVATE_KEY=<rotated-wireguard-private-key>
```

## Commands and results

Render the chart:

```sh
helm template test kubernetes/media
```

Expected resources include:

```text
ServiceAccount media-infisical-sync
Secret media-infisical-identity
InfisicalConnection media-infisical
InfisicalAuth media-infisical
InfisicalStaticSecret protonvpn-credentials
```

Validate against live CRDs without applying:

```sh
helm template test kubernetes/media > /tmp/media-infisical-render.yaml
kubectl apply --dry-run=server -f /tmp/media-infisical-render.yaml
```

Run repository checks:

```sh
kubernetes/test-helm-chart.sh
./scripts/check-storage-policy.sh
```

Expected storage result:

```text
storage policy ok
```

## Final outcome

The committed media WireGuard private key was removed from Git. Infisical now
owns the `protonvpn-credentials` Kubernetes Secret used by VPN-enabled media
workloads.
