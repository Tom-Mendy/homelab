# Coder agent workspaces

Coder 2.35.3 runs the control plane in `coder`; workspace Deployments and their
NFS-backed homes run in `coder-workspaces`. Stopping a workspace removes its
Deployment but retains its PVC. Deleting the workspace is the explicit data
deletion boundary.

## Before Flux reconciliation

Create `CODER_OIDC_CLIENT_SECRET` under `/oidc` in the existing Infisical
project. It must contain the same high-entropy value for both Coder and the
Authentik provider. Add intended users to the Authentik `coder-users` group;
`homelab-admins` already has access.

## First deployment

```sh
flux reconcile kustomization flux-system --with-source
kubectl wait -n coder --for=condition=Ready cluster/coder-postgres --timeout=10m
kubectl rollout status -n coder deployment/coder --timeout=10m
```

Open `https://coder.home.tom-mendy.com`, sign in through Authentik, and finish
the owner bootstrap if Coder requests it.

## Optional Coder Agents integration

Coder Agents and its AI Gateway require a Coder license entitlement. Check the
deployment before trying to configure Ollama:

```sh
curl -fsS https://coder.home.tom-mendy.com/api/v2/entitlements \
  | jq '.features | {aibridge, managed_agent_limit}'
```

The Community deployment currently reports both features as `not_entitled`.
Standard Coder workspaces and the independent Hermes workspace still work.

If those features become entitled, configure Coder Agents once in
**Admin settings > AI**:

1. Add an `OpenAI Compatible` provider named `ollama`.
2. Use base URL `http://ollama.ollama.svc.cluster.local:11434/v1` and API key
   `ollama` (Ollama ignores it, but Coder requires a value).
3. Under **Admin settings > AI > Models**, add `gemma4:e4b`, set the context
   limit to `32768`, and make it the default.
4. Grant the `Coder Agents User` organization role only to users who need it.

Provider settings live in Coder's PostgreSQL database. They are deliberately
not seeded through deprecated environment variables.

## Publish workspace templates

Install and authenticate the matching Coder CLI, then push each directory:

```sh
coder login https://coder.home.tom-mendy.com
coder templates push agent-workspace \
  --directory kubernetes/coder/workspace-templates/agent-workspace
coder templates push hermes-personal \
  --directory kubernetes/coder/workspace-templates/hermes-personal
```

Create only one `hermes-personal` workspace and disable its automatic stop in
the Coder schedule. The namespace quota permits Hermes plus two standard
workspaces, matching the cluster's intended capacity.

Before creating it, set `/matrix/HERMES_MATRIX_ALLOWED_USERS` in Infisical to
the full Matrix ID of each human allowed to use the bot. The Matrix chart
synchronizes it and `HERMES_MATRIX_ACCESS_TOKEN` into the `coder-workspaces`
namespace. The template injects those values without writing the token to the
workspace PVC.

## Forgejo access

Each standard workspace creates an Ed25519 key in its persistent home. On its
first start, copy the public key printed in the startup log and add it to the
Forgejo account, then run:

```sh
git clone --branch main \
  ssh://git@forgejo.forgejo.svc.cluster.local/Tom-Mendy/homelab.git \
  ~/project
```

No Forgejo token is stored in the template or Kubernetes Secret.

## Hermes first-time setup

The Hermes template uses the official v0.18.0 image (`v2026.7.1`). In the
workspace terminal, authenticate Hermes directly with the ChatGPT subscription
using its device-code flow, then select the external Hindsight service:

```sh
hermes auth add openai-codex
hermes model
hermes memory setup
hermes memory status
```

Choose `OpenAI Codex` in `hermes model`, then `hindsight` and `Local External`
in the memory wizard. Use
`http://hindsight.agent.svc.cluster.local:8888` as the API URL and leave the
optional API key blank. Restart the workspace afterward; its startup script
launches `hermes gateway run` when `/opt/data/config.yaml` exists. Hindsight's
embedded PostgreSQL data remains on its own `nfs-k8s` PVC in `agent`.

## Recovery check

Both templates create Deployments, so Kubernetes replaces their Pods after a
worker failure. Verify each direction during a maintenance window:

```sh
kubectl get pods -n coder-workspaces -o wide
kubectl drain node2 --ignore-daemonsets --delete-emptydir-data
kubectl get pods -n coder-workspaces -w
kubectl uncordon node2
kubectl drain node3 --ignore-daemonsets --delete-emptydir-data
kubectl get pods -n coder-workspaces -w
kubectl uncordon node3
```

Do not run both drains together. Confirm the replacement Pod reaches `Running`
and its home contents remain present before continuing.
