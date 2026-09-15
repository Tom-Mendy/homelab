# Repair Forgejo authentik SSO

## Problem

Forgejo redirected users to authentik, but authentik rejected the request with
an invalid or missing `client_id`. Launching Forgejo from the authentik portal
also opened the anonymous Forgejo home page rather than starting SSO.

## Investigation and reasoning

The authentik provider was correct: its client ID was `forgejo` and its
redirect URI matched Forgejo. The Forgejo `login_source` record existed but
its non-sensitive client ID and discovery URL fields were empty.

The OIDC setup runs from a pod lifecycle hook. A ConfigMap update changes the
mounted script without restarting the existing pod, so the corrected script
had not been run by the current Forgejo pod. The fix makes the CLI use the
actual Forgejo configuration file explicitly and adds a pod-template checksum
of the script, causing a rollout whenever the script changes.

```sh
kubectl -n forgejo exec deployment/forgejo -- sh -c \
  'su-exec git forgejo admin auth list'
kubectl -n forgejo exec deployment/forgejo -- sh -c \
  'sqlite3 /data/gitea/gitea.db ...'
```

The source list showed `authentik` as active. The SQLite inspection showed an
empty client ID and discovery URL, which explains authentik's rejection.

```sh
kubectl -n authentik exec deployment/authentik-worker -- ak shell -c '...'
```

Authentik already contained the Forgejo, Radarr, and Sonarr applications.
Radarr and Sonarr were assigned to the embedded outpost, and the administrator
account had access through `homelab-admins`.

## Outcome

The Forgejo OIDC hook now consistently configures the intended database and
runs again after a GitOps script change. The Forgejo authentik application now
launches `/user/oauth2/authentik`, so an authentik portal click starts the SSO
flow immediately. Radarr and Sonarr do not need to be created again.
