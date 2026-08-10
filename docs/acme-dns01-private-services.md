# ACME DNS-01 for private homelab services

This setup gives browser-trusted HTTPS certificates **without** installing
a private CA on clients and **without** exposing apps publicly.

## Domain pattern

Internal services use:

- `*.home.tom-mendy.com`

Examples currently present in DNS mapping (`kubernetes/blocky/config.yml`):

- `argocd.home.tom-mendy.com`
- `forgejo.tom-mendy.com`
- `grafana.home.tom-mendy.com`
- `homepage.home.tom-mendy.com`
- `keel.home.tom-mendy.com`
- `navidrome.home.tom-mendy.com`
- `openwebui.home.tom-mendy.com`
- `ollama.home.tom-mendy.com`
- `prometheus.home.tom-mendy.com`
- `trilium.home.tom-mendy.com`
- `vaultwarden.home.tom-mendy.com`

## Why DNS-01

Let's Encrypt validates domain ownership via DNS TXT records.
No inbound public access to your cluster is required.

## DNS provider note (Hostinger)

Traefik's ACME DNS challenge uses LEGO DNS providers.
If your DNS provider is not supported directly, use a supported DNS provider
for your authoritative zone (Cloudflare is commonly used).

## Required DNS records

For DNS-01 certificate issuance, the authoritative public zone must be
manageable by your DNS API token.

Practical options:

1. **Private-only resolution in LAN**: keep service A records in Blocky
   (`customDNS.mapping`) and use DNS-01 only for certificate issuance.
2. **Public DNS records**: publish A records to your ingress IP if that matches
   your security model.

## Apply steps

1. Create a Cloudflare API token with Zone DNS edit permission for `tom-mendy.com`.
2. Store the token in Infisical project `homelab`, env `prod`, path `/traefik`:

```text
CF_DNS_API_TOKEN=<rotated-cloudflare-dns-token>
```

1. Enable the Traefik Infisical sync after filling the real Infisical
   `identityID` in `kubernetes/traefik/values.yaml`:

```yaml
infisicalSecret:
  enabled: true
  identityID: "<machine-identity-id>"
```

The fallback example below is only for manual break-glass use. Do not commit
real token values.

```bash
kubectl apply -f kubernetes/traefik/traefik-cloudflare-secret.example.yaml
```

1. Deploy updated Traefik and apps:

```bash
cd ansible
./run.sh playbooks/deploy-apps.yml
```

or render/apply the local charts directly for a manual break-glass run:

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update
helm upgrade --install traefik traefik/traefik \
  -n traefik --create-namespace \
  -f kubernetes/traefik/values.yaml
helm upgrade --install blocky kubernetes/blocky -n blocky --create-namespace
helm upgrade --install navidrome kubernetes/navidrome -n navidrome --create-namespace
helm upgrade --install vaultwarden kubernetes/vaultwarden -n vaultwarden --create-namespace
```

1. Verify certificate issuance:

```bash
kubectl -n traefik logs deploy/traefik | grep -Ei "acme|certificate|letsencrypt|dns-01"
```

1. Verify host routing and certificate presentation:

```bash
curl -Ik https://keel.home.tom-mendy.com
curl -Ik https://vaultwarden.home.tom-mendy.com
```

## Result

Browsers trust certificates for these domains using public CA trust roots,
with no client CA installation.
