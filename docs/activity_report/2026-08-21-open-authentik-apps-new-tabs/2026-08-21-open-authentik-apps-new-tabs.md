# Open Authentik Applications in New Tabs

## Problem

Applications launched from the Authentik dashboard opened in the current
browser tab. The requested behavior was to open each dashboard application in a
new browser tab.

## Reasoning and investigation

The repository stores the Authentik application definitions in a blueprint:

```sh
rg -n -i "authentik|application|open.*tab|target" kubernetes docs
sed -n '1,260p' kubernetes/authentik/blueprints/oidc-clients.yaml
```

Authentik supports the `open_in_new_tab` application attribute. The existing
blueprint defines the applications that appear on the dashboard, so the change
was made there rather than as a manual dashboard edit. This keeps the setting
under Git and allows the Authentik extras HelmRelease to reconcile it again.

The applications found in the blueprint were Hindsight, Radarr, Sonarr,
qBittorrent, Open WebUI, Forgejo, Grafana, Flux, Coder, and Matrix.

## Commands and results

The following command located the application definitions and confirmed that
the setting was not already present:

```sh
rg -n -B 2 -A 12 'model: authentik_core.application' \
  kubernetes/authentik/blueprints/oidc-clients.yaml
```

The blueprint was then updated by adding `open_in_new_tab: true` to all ten
application definitions.

Validation succeeded:

```sh
git diff --check
# no output; exit status 0

helm lint kubernetes/authentik
# [INFO] Chart.yaml: icon is recommended
# 1 chart(s) linted, 0 chart(s) failed

./scripts/check-storage-policy.sh
# storage policy ok
```

No command failed during this activity.

## Outcome

All ten Authentik dashboard applications defined in the repository now have
`open_in_new_tab: true`. After Flux reconciles the Authentik extras release,
clicking one of these applications from the dashboard will open its launch URL
in a new browser tab or window, subject to the browser's popup policy.
