# Fix VPN Sidecar CrashLoops

## Problem

The remaining `CrashLoopBackOff` pods were VPN-routed workloads:

- `media/nzbget`
- `media/qbittorrent`
- `searxng/searxng`

In each case the application container was not the root failure. The `gluetun`
sidecar was crashing.

## Reasoning and Commands

Check the previous `gluetun` logs:

```sh
kubectl logs -n media deploy/qbittorrent -c gluetun --previous --tail=80
kubectl logs -n media deploy/nzbget -c gluetun --previous --tail=80
kubectl logs -n searxng deploy/searxng -c gluetun --previous --tail=80
```

Result:

```text
Wireguard settings: private key is not valid:
wgtypes: failed to parse base64-encoded key: illegal base64 data at input byte 0
```

Check only the shape of the generated Kubernetes Secrets, without printing the
secret values:

```sh
for ns_secret in media/protonvpn-credentials searxng/searxng-vpn-secret; do
  ns=${ns_secret%/*}
  sec=${ns_secret#*/}
  printf '%s\n' "$ns_secret"
  kubectl get secret -n "$ns" "$sec" -o json |
    jq -r '.data.WIREGUARD_PRIVATE_KEY | @base64d | {
      length:length,
      raw_valid:test("^[A-Za-z0-9+/]{43}=$"),
      contains_valid_key:(match("[A-Za-z0-9+/]{43}=") != null)
    }'
done
```

The values were not raw-valid WireGuard private keys, but they did contain a
valid 44-character key. The extra text came from the Infisical template using:

```text
{{ .WIREGUARD_PRIVATE_KEY }}
```

The Infisical operator exposes a secret object there. Stringifying the object
produced extra metadata around the value. The correct field is:

```text
{{ .WIREGUARD_PRIVATE_KEY.Value }}
```

An attempted `regexFind` template was rejected by the operator because the
input was not a string:

```text
wrong type for value; expected string; got model.SecretTemplateOptions
```

## Changes

Changed both Infisical templates to render the actual secret value:

```text
kubernetes/media/templates/infisical-secret.yaml
kubernetes/searxng/templates/infisical-secret.yaml
```

SearXNG still reported `OutOfSync` after the pods recovered because Keel had
updated the live `gluetun` sidecar image. The healthy live digest was pinned in
the chart:

```text
qmcgaw/gluetun:latest@sha256:bd84f4f090ca61170c8329a72d4f451255b01f6489486a621bfcb89749fb80ab
```

The live SearXNG `InfisicalStaticSecret` was patched and generated a raw-valid
secret immediately:

```sh
kubectl patch infisicalstaticsecret -n searxng searxng-secrets --type=json \
  -p='[{"op":"replace","path":"/spec/targets/1/template/data/WIREGUARD_PRIVATE_KEY","value":"{{ .WIREGUARD_PRIVATE_KEY.Value }}"}]'
kubectl annotate infisicalstaticsecret -n searxng searxng-secrets force-sync="$(date +%s)" --overwrite
```

The media object was reverted by Argo CD self-heal before the generated Secret
changed, so the Git change had to be pushed first.

## Verification

Storage policy:

```sh
./scripts/check-storage-policy.sh
```

Expected:

```text
storage policy ok
```

After Argo CD syncs the Git change, verify the generated Secrets are raw-valid:

```sh
for ns_secret in media/protonvpn-credentials searxng/searxng-vpn-secret; do
  ns=${ns_secret%/*}
  sec=${ns_secret#*/}
  printf '%s ' "$ns_secret"
  kubectl get secret -n "$ns" "$sec" -o json |
    jq -r '.data.WIREGUARD_PRIVATE_KEY | @base64d | test("^[A-Za-z0-9+/]{43}=$")'
done
```

Restart the affected deployments after both values are valid:

```sh
kubectl rollout restart -n media deploy/qbittorrent deploy/nzbget
kubectl rollout restart -n searxng deploy/searxng
```

## Outcome

The root cause is the Infisical template field, not the application images or
storage. Rendering `.Value` gives Gluetun the raw WireGuard key it expects.
