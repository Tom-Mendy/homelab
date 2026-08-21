# Fix qBittorrent Authentik SSO

## Problem

The qBittorrent WebUI continued to display its own username/password login
after Authentik authentication was enabled on the Traefik Ingress. Authentik
was redirecting unauthenticated browser requests correctly, but qBittorrent
was still challenging the authenticated request.

## Reasoning and commands

The repository already contained an Authentik forward-auth middleware and an
init container that added the qBittorrent subnet whitelist:

```sh
sed -n '1,280p' kubernetes/media/templates/qbittorrent.yaml
rg -n -C 12 'qbittorrent' kubernetes/authentik/blueprints/oidc-clients.yaml
```

The initial cluster inspection was blocked by the command sandbox:

```text
Unable to connect to the server: dial tcp 10.0.0.21:6443:
socket: operation not permitted
```

With read-only Kubernetes access, the workload and Ingress were inspected:

```sh
kubectl -n media get pod -l app=qbittorrent -o wide
kubectl -n media get ingress qbittorrent-ingress -o yaml
kubectl -n media logs deploy/qbittorrent -c qbittorrent --tail=180
kubectl -n media exec deploy/qbittorrent -c qbittorrent -- \
  sh -c "grep -n -F 'AuthSubnet' /config/qBittorrent/qBittorrent.conf || true"
```

The pod was healthy and the Ingress had the expected middleware, but the
active qBittorrent configuration contained no `AuthSubnetWhitelist` keys.
The init container had completed successfully. The direct external request
confirmed the exact symptom boundary:

```text
HTTP/2 302
location: https://authentik.home.tom-mendy.com/application/o/authorize/...
```

The LinuxServer image was then inspected to identify the startup behavior:

```sh
kubectl -n media exec deploy/qbittorrent -c qbittorrent -- sh -c \
  "sed -n '1,160p' /etc/s6-overlay/s6-rc.d/svc-qbittorrent/run"
```

The image starts qBittorrent with `/app/qbittorrent-nox --webui-port=8080`.
The qBittorrent configuration supports the subnet whitelist, but reverse
proxy support and the trusted proxy list also need to be explicit so the
forwarded client address is handled consistently.

A reversible runtime test backed up the configuration, stopped qBittorrent,
added the five settings, and started it again. All five settings remained
present after qBittorrent startup:

```ini
WebUI\AuthSubnetWhitelistEnabled=true
WebUI\AuthSubnetWhitelist=10.233.64.0/18
WebUI\LocalHostAuth=false
WebUI\ReverseProxySupportEnabled=true
WebUI\TrustedReverseProxiesList=10.233.64.0/18
```

The temporary runtime backup was removed after the test.

## Validation results

The Helm chart and storage policy checks passed:

```sh
helm lint kubernetes/media
# 1 chart(s) linted, 0 chart(s) failed

./scripts/check-storage-policy.sh
# storage policy ok
```

The full server dry-run reported immutable-field errors for existing bound
PVCs because the rendered chart does not include their live `volumeName`.
The qBittorrent ConfigMap and Deployment were then validated separately:

```sh
kubectl apply --dry-run=server -f /tmp/qbittorrent-sso-dry-run.yaml
# configmap/qbittorrent-sso configured (server dry run)
# deployment.apps/qbittorrent configured (server dry run)
```

The corrected ConfigMap and Deployment were applied, followed by a controlled
rollout:

```sh
kubectl apply -f /tmp/qbittorrent-sso-dry-run.yaml
kubectl -n media rollout restart deployment/qbittorrent
kubectl -n media rollout status deployment/qbittorrent --timeout=180s
# deployment "qbittorrent" successfully rolled out
```

After the rollout, all five settings were still present. A first API probe
immediately after the rollout failed with `Connection refused` while the
NymVPN sidecar was becoming ready. The retry succeeded:

```text
HTTP/1.1 200 OK
content-type: text/plain; charset=UTF-8
v5.2.2
```

The external Ingress continued to redirect unauthenticated users to Authentik:

```text
HTTP/2 302
location: https://authentik.home.tom-mendy.com/application/o/authorize/...
```

## Final outcome

`kubernetes/media/templates/qbittorrent.yaml` now configures qBittorrent for
the Authentik reverse-proxy flow by setting the whitelist, disabling the local
authentication challenge, enabling reverse-proxy support, and trusting the
Traefik pod CIDR. Authentik remains the external authentication boundary, and
qBittorrent no longer adds its own login challenge to requests arriving from
Traefik.
