# Pin Helm Chart Versions

## Problem

Several Argo CD applications used `targetRevision: "*"`, which lets Argo CD
resolve the newest Helm chart version. With automated sync enabled, that can
upgrade infrastructure components without an explicit repository change.

## Reasoning

The safest first pinning pass was to keep the exact chart versions already
deployed in the cluster. That changes GitOps reproducibility without changing
runtime manifests.

Commands used to inspect the live Argo CD revisions:

```sh
kubectl get applications.argoproj.io -n argocd \
  nfs-provisioner traefik keel grafana cloudnative-pg infisical-operator \
  infisical authentik prometheus \
  -o json \
  | jq -r '
      .items[]
      | [.metadata.name, (.status.sync.revisions // [] | join(","))]
      | @tsv
    '
```

Observed output:

```text
nfs-provisioner	4.0.18,4698118bed678972e73523b8c7a1f38130bb5197
traefik	40.2.0,fb833f57582261a6c2daeccf1c5f44bf9b1a5fa7,fb833f57582261a6c2daeccf1c5f44bf9b1a5fa7
keel	1.2.0,fb833f57582261a6c2daeccf1c5f44bf9b1a5fa7,fb833f57582261a6c2daeccf1c5f44bf9b1a5fa7
grafana	12.4.1,4698118bed678972e73523b8c7a1f38130bb5197,4698118bed678972e73523b8c7a1f38130bb5197
cloudnative-pg	0.28.2,7200e2b6e0685b219c9f6e3cc8957fee96565f76
infisical-operator	0.11.0,fb833f57582261a6c2daeccf1c5f44bf9b1a5fa7
infisical	1.8.0,4698118bed678972e73523b8c7a1f38130bb5197
authentik	2026.5.2,4698118bed678972e73523b8c7a1f38130bb5197,4698118bed678972e73523b8c7a1f38130bb5197
prometheus	29.9.0,fb833f57582261a6c2daeccf1c5f44bf9b1a5fa7,fb833f57582261a6c2daeccf1c5f44bf9b1a5fa7
```

The first revision for each multi-source application is the Helm chart version.
The later revisions are Git commits from the homelab values/manifests source.

## Changes

Pinned these chart revisions:

- `nfs-provisioner`: `4.0.18`
- `traefik`: `40.2.0`
- `keel`: `1.2.0`
- `grafana`: `12.4.1`
- `cloudnative-pg`: `0.28.2`
- `infisical-operator`: `0.11.0`
- `infisical`: `1.8.0`
- `authentik`: `2026.5.2`
- `prometheus`: `29.9.0`

## Outcome

The Argo CD applications no longer depend on floating Helm chart versions.
Future chart upgrades now require an explicit Git change.

Validation:

```text
storage policy ok
Success: No issues found in 3 files
application.argoproj.io/nfs-provisioner configured (server dry run)
application.argoproj.io/traefik configured (server dry run)
application.argoproj.io/keel configured (server dry run)
application.argoproj.io/grafana configured (server dry run)
application.argoproj.io/cloudnative-pg configured (server dry run)
application.argoproj.io/infisical-operator configured (server dry run)
application.argoproj.io/infisical configured (server dry run)
application.argoproj.io/authentik configured (server dry run)
application.argoproj.io/prometheus configured (server dry run)
```
