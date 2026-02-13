# ACME DNS-01 for private homelab services

This setup gives browser-trusted HTTPS certificates **without** installing a private CA on clients and **without** exposing apps publicly.

## Domain pattern

Services are moved to:

- `keel.home.tom-mendy.com`
- `navidrome.home.tom-mendy.com`
- `vaultwarden.home.tom-mendy.com`

## Why DNS-01

Let's Encrypt validates domain ownership via DNS TXT records. No inbound public access to your cluster is required.

## DNS provider note (Hostinger)

Traefik's ACME DNS challenge uses LEGO DNS providers. If your DNS provider is not supported directly, use a supported DNS provider for your authoritative zone (Cloudflare is commonly used).

## Required DNS records

In Cloudflare DNS (or your supported provider), create:

- `keel.home.tom-mendy.com` -> `192.168.1.20` (A)
- `navidrome.home.tom-mendy.com` -> `192.168.1.20` (A)
- `vaultwarden.home.tom-mendy.com` -> `192.168.1.20` (A)

If you only want those records usable inside your LAN, keep using Blocky custom DNS and avoid publishing public A records.

## Apply steps

1. Create a Cloudflare API token with zone DNS edit permission for `tom-mendy.com`.
2. Apply the Traefik secret (replace token first):

```bash
kubectl apply -f kubernetes/traefik/traefik-cloudflare-secret.example.yaml
```

1. Deploy updated Traefik and apps:

```bash
cd ansible
./run.sh playbooks/deploy-apps.yml
```

or with kubectl only:

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update
helm upgrade --install traefik traefik/traefik -n traefik --create-namespace -f kubernetes/traefik/traefik-values.yaml
kubectl apply -f kubernetes/blocky/blocky.yaml
kubectl apply -f kubernetes/keel/keel-ingress.yaml
kubectl apply -f kubernetes/navidrome/navidrome.yaml
kubectl apply -f kubernetes/vaultwarden/vaultwarden.yaml
```

1. Verify certificate issuance:

```bash
kubectl -n traefik logs deploy/traefik | grep -Ei "acme|certificate|letsencrypt|dns-01"
```

## Result

Browsers trust certificates for these domains using public CA trust roots, with no client certificate installation.
