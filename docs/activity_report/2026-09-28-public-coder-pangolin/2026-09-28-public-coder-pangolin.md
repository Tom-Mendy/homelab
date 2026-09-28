# Public Coder access through Pangolin

## Problem

Coder was configured with the private hostname
`coder.home.tom-mendy.com`. Forgejo already uses the public Pangolin/Newt path
with Authentik and the canonical `*.tom-mendy.com` naming scheme. Coder needs the
same secure public entry point while keeping the Kubernetes service private.

## Design

The public hostname is `coder.tom-mendy.com`.

The request path is:

```text
Browser
  -> public DNS coder.tom-mendy.com
  -> Pangolin HTTPS resource
  -> Newt tunnel in the homelab
  -> Traefik LoadBalancer 10.0.0.60
  -> Coder ClusterIP service
  -> Authentik OIDC
```

Coder remains a ClusterIP service. No NodePort, LoadBalancer, or direct VNC
endpoint is added. WebSocket forwarding must remain enabled in the Pangolin
HTTPS resource because Coder uses WebSockets for the agent and terminal paths.

## GitOps changes

- `kubernetes/coder/values.yaml` now uses
  `https://coder.tom-mendy.com` for `CODER_ACCESS_URL` and its Traefik host.
- Authentik's Coder provider now accepts only the public OIDC callback and uses
  the public launch URL.
- Blocky maps `coder.tom-mendy.com` to the internal Traefik address for LAN
  clients, while public DNS continues to point to Pangolin.
- The homepage and Coder documentation use the public URL.
- The previous `coder.home.tom-mendy.com` Blocky mapping is removed because the
  Coder Ingress now has the public canonical host.

## External Pangolin and DNS steps

These steps cannot be represented in this Git repository because they are
stored in the Pangolin VPS/control-plane configuration:

1. Create the public DNS record:

   ```text
   coder.tom-mendy.com A <Pangolin public IPv4>
   ```

   The currently observed public address of `pangolin.tom-mendy.com` is
   `92.222.90.223`; verify the address in the Pangolin/Hostinger account before
   saving the record.
2. In Pangolin, create an HTTPS resource for `coder.tom-mendy.com`.
3. Route it through the existing Newt connector (`main-tunnel`) to the internal
   Traefik HTTP entrypoint, using the same target pattern as Forgejo. Keep
   WebSockets enabled and do not expose port 6080 or VNC directly.
4. Ensure the Pangolin/VPS firewall allows TCP 443. No new Kubernetes firewall
   port is required.
5. Keep the resource protected by Coder's Authentik OIDC login. Do not enable
   anonymous access or public registration.

## Reconciliation and verification

After merging/pushing the GitOps branch:

```sh
flux reconcile source git flux-system
flux reconcile helmrelease coder -n flux-system --with-source
flux reconcile helmrelease authentik-extras -n flux-system --with-source
flux reconcile helmrelease blocky -n flux-system --with-source
kubectl get ingress -n coder
kubectl get svc -n coder
kubectl logs -n newt-system deploy/newt --tail=100
```

Verify from an external network, not only the homelab LAN:

```sh
curl -fsSI https://coder.tom-mendy.com/
websocat wss://coder.tom-mendy.com/api/v2/agent/example  # use a real Coder session
```

Then sign in through Authentik and confirm that Coder redirects back to
`https://coder.tom-mendy.com/api/v2/users/oidc/callback` without an issuer or
redirect URI mismatch.

## Security result

The public surface is only HTTPS on the Pangolin endpoint. Authentik controls
human login, Coder controls workspace authorization, and the desktop app
remains owner-only behind Coder's application proxy. Direct VNC access is not
introduced.
