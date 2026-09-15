# Add Authentik SSO to qBittorrent

## Problem

`https://qbittorrent.home.tom-mendy.com` was only protected by qBittorrent's own
WebUI login (username/password). Radarr and Sonarr already authenticate through
the Authentik forward-auth middleware `media-authentik-media`, but qBittorrent
was not part of that flow, so there was no single browser login for the media
stack.

## Reasoning and commands

### State inspection

Radarr and Sonarr use the `forward_single` Authentik proxy provider pattern:
the middleware `authentik-media` in the `media` namespace forwards every request
to the embedded Authentik outpost, and the app itself has its own login disabled.

```sh
kubectl -n media get middlewares,ingress
kubectl -n media get ingress qbittorrent-ingress -o jsonpath='{.metadata.annotations}'
```

The middleware exists and the qBittorrent ingress had no middleware annotation.
qBittorrent is different from Radarr/Sonarr: it always requires its own WebUI
login. qBittorrent does not support trusting proxy auth headers, so putting the
middleware in front would produce a double login (Authentik, then qBittorrent).

### qBittorrent settings needed

qBittorrent supports "Bypass authentication for clients in whitelisted IP
subnets". The keys live under `[Preferences]` in `/config/qBittorrent/qBittorrent.conf`:

```ini
WebUI\AuthSubnetWhitelistEnabled=true
WebUI\AuthSubnetWhitelist=10.233.64.0/18
```

The whitelist is the cluster pod CIDR, which contains the Traefik pod IP
(`10.233.75.28` at the time of writing). Requests proxied by Traefik therefore
skip the qBittorrent login, and Authentik becomes the only external login.
Internal pods in that CIDR can reach the WebUI without auth, an accepted risk
identical to the internal-open posture of Radarr/Sonarr.

```sh
kubectl get pods -n traefik -o wide   # Traefik pod IP is inside 10.233.64.0/18
kubectl -n media exec deploy/qbittorrent -c qbittorrent -- \
  cat /config/qBittorrent/qBittorrent.conf   # existing [Preferences] WebUI keys
```

### Config seeding as GitOps

The conf lives on the NFS PVC and qBittorrent rewrites it on every save, so a
read-only ConfigMap mounted over the file would break. The chosen approach is an
`initContainer` that idempotently sets-or-inserts the two keys into the
`[Preferences]` section before qBittorrent starts. Naively appending at the end
of the file would group the keys under the last section (`[RSS]`), so the
script inserts them before the first `[` line that follows `[Preferences]`.

```sh
helm template media kubernetes/media --namespace media
kubectl apply --dry-run=server -f /tmp/media-rendered.yaml
```

### The awk backslash trap

The first script version passed the key to awk with `-v k="$key"`. Running it
against a copy of the real conf produced:

```text
awk: warning: escape sequence `\A' treated as plain `A'
```

awk processes backslash escapes in `-v` values, so `WebUI\AuthSubnetWhitelist`
became `WebUIAuthSubnetWhitelist` and the key was corrupted. Fix: export the
key as an environment variable and read it with `ENVIRON["KEY"]`, which awk
does not escape-process.

## Command results

The chart and blueprint lints, the Flux kustomization, and the storage policy
check all passed:

```sh
helm lint kubernetes/media                      # 0 chart(s) failed
helm lint kubernetes/authentik                  # 0 chart(s) failed
helm template media kubernetes/media --namespace media   # renders
kubectl apply --dry-run=server -f /tmp/media-rendered.yaml
kubectl kustomize kubernetes/flux/cluster/apps \
  --load-restrictor LoadRestrictionsNone       # renders
./scripts/check-storage-policy.sh               # storage policy ok
```

The script was tested against a copy of the live qBittorrent.conf in three
scenarios, all passing:

```sh
SSO_AUTH_WHITELIST=10.233.64.0/18 bash /tmp/ensure-sso-auth-test.sh
# [Preferences] gained:
#   WebUI\AuthSubnetWhitelistEnabled=true
#   WebUI\AuthSubnetWhitelist=10.233.64.0/18
```

Second run produced no diff (idempotent). A fresh conf without a `[Preferences]`
section gets one appended, and a conf with stale whitelist values has them
replaced in place.

## Outcome

- `kubernetes/authentik/blueprints/oidc-clients.yaml`: added the `qbittorrent-users`
  group, the `qbittorrent-provider` proxy provider (`forward_single`, external
  host `https://qbittorrent.home.tom-mendy.com`), the `qbittorrent` application,
  policy bindings for `homelab-admins` and `qbittorrent-users`, and registered
  the provider on the embedded outpost.
- `kubernetes/media/templates/qbittorrent.yaml`: created the `qbittorrent-sso`
  ConfigMap with the seeding script, added the `sso-config` initContainer, the
  `sso-script` volume, and the `media-authentik-media@kubernetescrd` middleware
  annotation on the ingress.
- `kubernetes/media/values.yaml` and `values.schema.json`: new `ssoAuthWhitelist`
  value (`10.233.64.0/18`) under `apps.qbittorrent`.

After Flux reconciles, `https://qbittorrent.home.tom-mendy.com` will require the
Authentik login and skip the qBittorrent WebUI login for proxied requests. If
`ssoAuthWhitelist` is removed, the ConfigMap, initContainer and middleware
annotation disappear again.
