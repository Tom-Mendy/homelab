# Authentik outpost hostname

The embedded Authentik outpost must use `https://authentik.tom-mendy.com` for
both `authentik_host` and `authentik_host_browser`. The proxy application
blueprints declare these values explicitly so the hostname does not depend on
the URL used during initial setup.

On 2026-10-18, the stored outpost configuration still used an obsolete hostname
and left `authentik_host_browser` empty. Requests to protected applications
therefore redirected to the wrong authorization endpoint.

For an existing installation, update these fields under Applications > Outposts
in the Authentik admin interface, or apply the proxy application blueprint.
If redirects still use the previous hostname, restart the server deployment to
reload the embedded outpost configuration:

```sh
kubectl -n authentik rollout restart deployment/authentik-server
kubectl -n authentik rollout status deployment/authentik-server
```

Verify unauthenticated requests to the protected applications return HTTP 302
with an authorization URL on `authentik.tom-mendy.com`. The `redirect_uri`
parameter must still point to the application's own
`/outpost.goauthentik.io/callback` endpoint.
