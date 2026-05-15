# 2026-05-15 Sync local Atuin account

<!-- markdownlint-disable MD013 -->

## Problem

The local Atuin client needed to sync with the self-hosted Atuin server at
`https://atuin.home.tom-mendy.com`.

The local client already existed:

```sh
command -v atuin
atuin --version
```

```text
/home/tmendy/.atuin/bin/atuin
atuin 18.13.3 (e737ba5b9a149eaec706418bc560e8ba7ea8c81b)
```

The local config had no active `sync_address`, so the default public Atuin
server would be used unless the self-hosted address was configured.

## Reasoning path

The Atuin documentation says self-hosted clients must set `sync_address` in
`~/.config/atuin/config.toml`, or use the `ATUIN_SYNC_ADDRESS` environment
variable. It also says `open_registration` controls whether the server accepts
new users.

The client config was backed up and updated:

```sh
cp "$HOME/.config/atuin/config.toml" "$HOME/.config/atuin/config.toml.bak"
```

The following settings were appended to `~/.config/atuin/config.toml`:

```toml
# Self-hosted sync server
sync_address = "https://atuin.home.tom-mendy.com"
auto_sync = true
```

The server was reachable:

```sh
curl -I https://atuin.home.tom-mendy.com
```

```text
HTTP/2 200
atuin-version: 18.12.0
content-type: application/json
```

Atuin doctor ran successfully:

```sh
atuin doctor
```

```text
Atuin Doctor
Checking for diagnostics

"version": "18.13.3",
"sync": null,
"default": "zsh",
"plugins": [
  "atuin"
]
```

Local zsh history was imported:

```sh
atuin import auto
```

```text
Importing history...
Detected ZSH
Importing history from zsh
Import complete!
```

The first registration attempt failed because registration was closed:

```sh
atuin register -u tmendy -e tom.mendy@epitech.eu
```

```text
Error: Invalid request to the service at https://atuin.home.tom-mendy.com/register, 400 Bad Request - this server is not open for registrations.
```

The live deployment confirmed the setting:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin get deploy atuin -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}'
```

```text
ATUIN_DB_URI=
USER_UID=1025
USER_GID=100
ATUIN_HOST=0.0.0.0
ATUIN_PORT=8888
ATUIN_OPEN_REGISTRATION=false
```

Argo CD self-heal reverted a direct live change, so the parent and Atuin Argo
applications were paused temporarily with explicit approval.

## Commands and results

Pause the parent and Atuin apps:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n argocd patch application homelab --type=json -p='[{"op":"remove","path":"/spec/syncPolicy"}]'
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n argocd patch application atuin --type=json -p='[{"op":"remove","path":"/spec/syncPolicy"}]'
```

```text
application.argoproj.io/homelab patched
application.argoproj.io/atuin patched
```

Open Atuin registration:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin set env deploy/atuin ATUIN_OPEN_REGISTRATION=true
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin rollout status deploy/atuin --timeout=120s
```

```text
deployment.apps/atuin env updated
deployment "atuin" successfully rolled out
```

Verify registration was open:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin get deploy atuin -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}'
```

```text
ATUIN_OPEN_REGISTRATION=true
```

The user then registered locally:

```sh
atuin register -u tmendy -e tom.mendy@epitech.eu
```

```text
Registration successful! Please make a note of your key (run 'atuin key') and keep it safe.
You will need it to log in on other devices, and we cannot help recover it if you lose it.
```

Registration was closed immediately:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin set env deploy/atuin ATUIN_OPEN_REGISTRATION=false
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin rollout status deploy/atuin --timeout=120s
```

```text
deployment.apps/atuin env updated
deployment "atuin" successfully rolled out
```

Verify registration was closed:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin get deploy atuin -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}'
```

```text
ATUIN_OPEN_REGISTRATION=false
```

Run the first sync:

```sh
atuin sync
```

```text
Uploading 1 records to 019da07dbc1a76b385b0be052e1fee19/history
2/0 up/down to record store
4974 in history index, but 907 in history store
Running automatic history store init...
Re-running sync due to new records locally
Uploading 4067 records to 019da07dbc1a76b385b0be052e1fee19/history
4068/0 up/down to record store
Sync complete! 4974 items in history database, force: false
```

Restore Argo CD auto-sync:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n argocd patch application homelab --type=json -p='[{"op":"add","path":"/spec/syncPolicy","value":{"automated":{"enabled":true,"prune":true,"selfHeal":true},"syncOptions":["CreateNamespace=true"]}}]'
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n argocd patch application atuin --type=json -p='[{"op":"add","path":"/spec/syncPolicy","value":{"automated":{"prune":true,"selfHeal":true},"syncOptions":["CreateNamespace=true"]}}]'
```

```text
application.argoproj.io/homelab patched
application.argoproj.io/atuin patched
```

## Final outcome

Local Atuin sync is configured and connected:

```sh
atuin status
```

```text
Atuin v18.13.3 - Build rev e737ba5b9a149eaec706418bc560e8ba7ea8c81b

[Local]
Sync frequency: 5m
Last sync: 2026-05-15 15:52:09.933435828 +09:00:00
[Remote]
Address: https://atuin.home.tom-mendy.com
Username: tmendy
```

Atuin is healthy and registration is closed:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n atuin get pods,deploy -o wide
```

```text
NAME                           READY   STATUS    RESTARTS   AGE     IP             NODE
pod/atuin-c9645898b-v99vq      1/1     Running   0          2m20s   10.233.71.48   node3
pod/postgres-7b68b458f-2gqzv   1/1     Running   0          30m     10.233.71.34   node3

NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/atuin      1/1     1            1           57d
deployment.apps/postgres   1/1     1            1           57d
```

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n argocd get application homelab -o jsonpath='{.status.sync.status} {.status.health.status}'
kubectl --kubeconfig "$HOME/.kube/config-homelab" -n argocd get application atuin -o jsonpath='{.status.sync.status} {.status.health.status}'
```

```text
Synced Healthy
Synced Healthy
```

The encryption key was not printed into logs. Run `atuin key` locally and store
the result in a password manager.
