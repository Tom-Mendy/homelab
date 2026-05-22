# Configure Forgejo OAuth2 Claims

## Problem

Forgejo needed to use the new OAuth2 claims from the identity provider for
automatic account creation. The required Forgejo setting,
`ENABLE_AUTO_REGISTRATION`, had been added to the chart, but it was mapped to
the wrong Forgejo configuration section.

Forgejo documents `ENABLE_AUTO_REGISTRATION` and `USERNAME` under
`[oauth2_client]`, not `[server]`.

## Reasoning path

Check the current Forgejo chart values and rendered deployment:

```sh
sed -n '1,180p' kubernetes/forgejo/templates/deployment.yaml
sed -n '1,140p' kubernetes/forgejo/values.yaml
sed -n '1,180p' kubernetes/forgejo/values.schema.json
```

The deployment template showed this incorrect environment variable:

```yaml
- name: FORGEJO__server__ENABLE_AUTO_REGISTRATION
  value: {{ .Values.enableAutoRegistration | quote }}
```

The Forgejo Configuration Cheat Sheet for latest, v15.0.2 on 2026-05-22,
documents the setting in the OAuth2 Client section:

```text
[oauth2_client]
ENABLE_AUTO_REGISTRATION
USERNAME
```

Update the chart so the settings render as OAuth2 client configuration:

```yaml
- name: FORGEJO__oauth2_client__ENABLE_AUTO_REGISTRATION
  value: {{ .Values.oauth2Client.enableAutoRegistration | quote }}
- name: FORGEJO__oauth2_client__USERNAME
  value: {{ .Values.oauth2Client.username | quote }}
```

Keep the username claim source configurable in `values.yaml`:

```yaml
oauth2Client:
  enableAutoRegistration: true
  username: nickname
```

## Command results

Render the Forgejo chart:

```sh
helm template test kubernetes/forgejo
```

Relevant output:

```yaml
env:
  - name: USER_UID
    value: "1023"
  - name: USER_GID
    value: "100"
  - name: FORGEJO__server__ROOT_URL
    value: "https://forgejo.tom-mendy.com/"
  - name: FORGEJO__oauth2_client__ENABLE_AUTO_REGISTRATION
    value: "true"
  - name: FORGEJO__oauth2_client__USERNAME
    value: "nickname"
  - name: FORGEJO__actions__ENABLED
    value: "true"
  - name: FORGEJO__actions__DEFAULT_ACTIONS_URL
    value: "https://data.forgejo.org"
```

Render all local Helm charts:

```sh
./kubernetes/test-helm-chart.sh
```

Output:

```text
=== blocky ===
OK
=== homepage ===
OK
=== traefik ===
OK
=== keel ===
OK
=== prometheus ===
OK
=== grafana ===
OK
=== navidrome ===
OK
=== vaultwarden ===
OK
=== forgejo ===
OK
=== forgejo-runner ===
OK
=== searxng ===
OK
=== endfield ===
OK
=== infisical-postgres ===
OK
=== authentik-postgres ===
OK
=== authentik ===
OK
```

Check the repository storage policy:

```sh
./scripts/check-storage-policy.sh
```

Output:

```text
storage policy ok
```

Confirm no active Kubernetes YAML uses `local-path`:

```sh
rg -n "local-path" kubernetes --glob '*.yaml' --glob '*.yml'
```

Output:

```text
```

## Final outcome

Forgejo now renders the documented OAuth2 client settings:

- `FORGEJO__oauth2_client__ENABLE_AUTO_REGISTRATION=true`
- `FORGEJO__oauth2_client__USERNAME=nickname`

The values schema now requires the `oauth2Client` block and restricts
`username` to Forgejo-supported claim source values: `userid`, `nickname`, or
`email`.

No storage changes were made. The existing Forgejo persistent volume remains a
static Synology NFS-backed PV with no node affinity, so the workload can
reschedule between worker nodes without depending on worker-local disk.
