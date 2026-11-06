# Public Radarr and Sonarr access

Radarr is available at `https://radarr.tom-mendy.com` and Sonarr at
`https://sonarr.tom-mendy.com`. Public DNS records are unproxied CNAMEs to
`pangolin.tom-mendy.com`. Blocky resolves both names to `10.0.0.60` on the LAN.

Requests pass through Pangolin, the existing Newt connector, Traefik HTTPS,
and the `media-authentik-media` forward-auth middleware. Pangolin resources
are maintained by the Newt blueprint in `kubernetes/newt/upstream-values.yaml`.
They target Traefik at `https://10.0.0.60:443`, using each public hostname for
both SNI and the Host header. Never point these resources directly at the
application services, because those services rely on external authentication.

Authentik applications, proxy providers, launch URLs, and callback ingresses
use the same public names. The login service is
`https://authentik.tom-mendy.com`. Radarr and Sonarr retain external
authentication, so users do not need a second application password.

Assign access in Authentik by adding users to `radarr-users` or `sonarr-users`.
The groups grant access independently. Members of `homelab-admins` can access
both. These groups grant the application's normal management access, not a
read-only view. Users with neither application group nor the admin group must
be denied. The former shared `media-users` bindings are removed; existing
members are migrated to both application groups to preserve their access.

Verify both public and LAN routes after changes:

```sh
curl -sSI https://radarr.tom-mendy.com/
curl -sSI https://sonarr.tom-mendy.com/
curl -sSI --resolve radarr.tom-mendy.com:443:10.0.0.60 \
  https://radarr.tom-mendy.com/
curl -sSI --resolve sonarr.tom-mendy.com:443:10.0.0.60 \
  https://sonarr.tom-mendy.com/
```

Anonymous requests, including application API paths, must enter the Authentik
login flow. Callback paths under `/outpost.goauthentik.io` must reach the
Authentik server. Check access with an allowed user and with a user outside
the application's groups. Keep the application services as ClusterIP and
retain the existing Synology NFS volumes.
