# Pin Floating Helm Chart Revisions

## Problem

Several Argo CD Helm applications used `targetRevision: "*"`. With automated
sync enabled, Argo could resolve newer chart versions without an explicit Git
change.

## Reasoning

The safe fix was to pin each chart to the version already deployed in the
cluster, then check that each version exists in the online Helm repository.

Live Argo CD revisions:

```sh
kubectl get applications.argoproj.io -n argocd \
  grafana cloudnative-pg prometheus infisical-operator traefik keel \
  infisical authentik nfs-provisioner \
  -o json \
  | jq -r '
      .items[]
      | [
          .metadata.name,
          (.status.health.status // ""),
          (.status.sync.status // ""),
          (.status.sync.revisions // [] | join(","))
        ]
      | @tsv
    '
```

Observed chart revisions:

```text
grafana              12.4.1
cloudnative-pg       0.28.2
prometheus           29.9.0
infisical-operator   0.11.0
traefik              40.2.0
keel                 1.2.0
infisical            1.8.0
authentik            2026.5.2
nfs-provisioner      4.0.18
```

Online Helm repository checks returned the same versions. The Infisical
operator repository reports chart version `v0.11.0`, and Helm accepts
`--version 0.11.0`; the Argo live revision is `0.11.0`, so that value was used.

## Changes

Pinned these Argo CD Helm app `targetRevision` values:

- `grafana`: `12.4.1`
- `cloudnative-pg`: `0.28.2`
- `prometheus`: `29.9.0`
- `infisical-operator`: `0.11.0`
- `traefik`: `40.2.0`
- `keel`: `1.2.0`
- `infisical`: `1.8.0`
- `authentik`: `2026.5.2`
- `nfs-provisioner`: `4.0.18`

## Outcome

The Helm chart apps no longer float to newer chart versions. Future chart
upgrades now require a visible Git diff.

Validation:

```text
rg -n 'targetRevision: "?\*' kubernetes/argocd/apps --glob '*.yaml'
# no matches

storage policy ok
Success: No issues found in 2 files

application.argoproj.io/grafana configured (server dry run)
application.argoproj.io/cloudnative-pg configured (server dry run)
application.argoproj.io/prometheus configured (server dry run)
application.argoproj.io/infisical-operator configured (server dry run)
application.argoproj.io/traefik configured (server dry run)
application.argoproj.io/keel configured (server dry run)
application.argoproj.io/infisical configured (server dry run)
application.argoproj.io/authentik configured (server dry run)
application.argoproj.io/nfs-provisioner configured (server dry run)
```
