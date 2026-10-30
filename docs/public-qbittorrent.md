# Public qBittorrent access

The canonical WebUI URL is `https://torrent.tom-mendy.com`.

## Request path

Browser -> Pangolin HTTPS -> Newt -> Traefik HTTPS -> Authentik forward-auth
-> qBittorrent ClusterIP port 8080.

The qBittorrent ingress keeps the `media-authentik-media` middleware. The
Authentik proxy provider and portal launch URL use the public hostname, and
`/outpost.goauthentik.io` is routed separately to the Authentik server for
login callbacks. Existing `homelab-admins` and `qbittorrent-users` access
bindings remain unchanged. Blocky resolves the public hostname to Traefik
(`10.0.0.60`) inside the LAN.

## External Pangolin configuration

Pangolin resources are managed outside this Git repository. Configure an HTTPS
resource for `torrent.tom-mendy.com` through the existing cluster Newt site.
Target Traefik at `https://10.0.0.60:443` with TLS server name
`torrent.tom-mendy.com`, preserving the original Host header. Validate the
backend certificate. Match the existing working Forgejo resource's forwarding
settings where appropriate.

Do not target `qbittorrent.media.svc.cluster.local:8080` directly: it bypasses
Traefik's Authentik middleware. qBittorrent trusts internal pod addresses for
its existing SSO setup, so a direct Newt target must not be published.
Pangolin authentication may be disabled only when this Authentik-protected
Traefik path is used. No BitTorrent peer ports are published by this change.

## Verification

```sh
curl -sSI --resolve torrent.tom-mendy.com:443:10.0.0.60 \
  https://torrent.tom-mendy.com/
curl -sSI https://torrent.tom-mendy.com/
```

An unauthenticated request must enter the Authentik login flow, not return the
qBittorrent WebUI. Verify login and return to the WebUI in a browser as an
authorized user. Public TLS and the internal route must be tested separately.
