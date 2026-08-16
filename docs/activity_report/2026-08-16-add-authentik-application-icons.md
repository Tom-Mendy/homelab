# Add icons to authentik applications

## Problem

The authentik user portal listed six managed applications, but only Forgejo had
an icon. The portal was harder to scan than necessary.

## Reasoning and commands

Each application icon is configured through its `meta_icon` URL in the
declarative authentik blueprint. The running applications were checked before
choosing their instance-hosted assets:

```sh
kubectl -n ollama exec statefulset/open-webui -- \
  curl -sS -o /dev/null -w '%{http_code} %{content_type}' \
  http://127.0.0.1:8080/static/favicon.png
kubectl -n grafana exec deployment/grafana -- \
  curl -sS -o /dev/null -w '%{http_code} %{content_type}' \
  http://127.0.0.1:3000/public/img/grafana_icon.svg
kubectl -n ollama exec statefulset/open-webui -- \
  curl -sS -H 'Host: flux.home.tom-mendy.com' -o /dev/null \
  -w '%{http_code} %{content_type}' \
  http://flux-operator.flux-system.svc.cluster.local:9080/favicon.svg
```

The three endpoints returned `200` with their expected PNG or SVG content
types. Forgejo already exposes `/assets/img/logo.svg`; Radarr and Sonarr use
their official upstream logo URLs because their instance logo endpoint returned
`500` during the previous check.

## Outcome

All six applications managed by the blueprint now declare `meta_icon`: Flux,
Forgejo, Grafana, Open WebUI, Radarr, and Sonarr. No workload, storage, or
access policy changed.
