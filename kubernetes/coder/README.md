# Coder agent workspaces

Coder 2.36.4 runs the control plane in `coder`; workspace Deployments and their
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

Open `https://coder.tom-mendy.com`, sign in through Authentik, and finish
the owner bootstrap if Coder requests it.

## Optional Coder Agents integration

Coder Agents and its AI Gateway require a Coder license entitlement. Check the
deployment before trying to configure Ollama:

```sh
curl -fsS https://coder.tom-mendy.com/api/v2/entitlements \
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

Commits to `main` that change a workspace template are validated and published
by Forgejo Actions. The workflow activates the new version and sets existing
workspaces from that template to update automatically the next time they start.
It requires a repository Actions secret named `CODER_SESSION_TOKEN` for a Coder
user that can publish templates and manage all existing workspaces built from
them. Keep the token dedicated to CI.

Existing running workspaces continue on their current build until they restart,
except Hermes. Publishing `hermes-personal` updates and starts the owner's
`nainjoueur/hermes` workspace, disables autostop, and verifies Kubernetes access
from inside it. The update briefly interrupts its Matrix gateway.

For a manual push, authenticate with the matching Coder CLI and run:

```sh
coder login https://coder.tom-mendy.com
coder templates push agent-workspace \
  --directory kubernetes/coder/workspace-templates/agent-workspace
coder templates push t3code \
  --directory kubernetes/coder/workspace-templates/t3code
coder templates push hermes-personal \
  --directory kubernetes/coder/workspace-templates/hermes-personal
```

If a workspace build reports `requested: requests.storage=50Gi`, the published
Coder template is stale. The versioned `t3code` template requests `10Gi`, so
republish it with the command above and retry the workspace. Do not increase
the namespace quota to hide this drift. Existing stopped workspaces retain
their PVCs, so delete an unused workspace only when its data is no longer
needed.

The `t3code` template is separate from `agent-workspace`. Its Debian-based
image installs Buildah; the workspace runs Buildah as UID 1000 without elevated
container privileges. Forgejo Actions builds the image from
`kubernetes/coder/workspace-images/t3code/Dockerfile` and publishes it to
Harbor. On first startup, the workspace installs Bun into its persistent home,
alongside T3, and compiles T3's Linux `node-pty` native module.

The `personal-desktop` template is a separate persistent graphical workspace. It
runs XFCE behind TigerVNC and noVNC on localhost:6080, exposed only through the
Coder application proxy as the owner-only `Desktop` app. Its home is a 50Gi NFS
PVC using `nfs-k8s`; it does not create a direct Ingress, NodePort, or public VNC
endpoint. Publish it with:

```sh
coder templates push personal-desktop \
  --directory kubernetes/coder/workspace-templates/personal-desktop
```

Create one stable workspace named `tom-personal-desktop`. Open the desktop from
`https://coder.tom-mendy.com` and the workspace's `Desktop` app tile. The
workspace survives laptop shutdowns, but it does not provide access to the G14's
local GPU.

Create only one `hermes-personal` workspace and disable its automatic stop in
the Coder schedule. The namespace quota permits Hermes plus two standard
workspaces, matching the cluster's intended capacity.

Before creating it, set `/matrix/HERMES_MATRIX_ALLOWED_USERS` in Infisical to
the full Matrix ID of each human allowed to use the bot. The Matrix chart
synchronizes it and `HERMES_MATRIX_ACCESS_TOKEN` into the `coder-workspaces`
namespace. The template injects those values without writing the token to the
workspace PVC.

The Hermes workspace includes Bun, the Coder CLI, Crane CLI, and `kubectl`,
installed into its persistent home at startup. The workspace
runs with the `hermes` ServiceAccount and explicitly mounts a rotating token,
granting cluster administrator access to manage and inspect cluster resources. Run
`coder login` with `https://coder.tom-mendy.com` to authenticate it as your
user. The workspace advertises `/usr/bin/bash` as its shell. Because the
container runs as an unprivileged user whose image-level login shell is
`/bin/sh`, its startup script also installs a small `~/.profile` fallback that
executes Bash for interactive SSH sessions. Non-interactive startup commands
continue to run through their explicitly selected interpreter.

## Hermes workspace image

The custom workspace image is built by Forgejo Actions from
`kubernetes/coder/workspace-images/hermes/Dockerfile`. It installs the stable
Debian system dependencies used for development and infrastructure work,
including `unzip` for Bun, while keeping the runtime user non-root. The template
pins this image by digest and pulls it using `portfolio-registry-auth` in
`coder-workspaces`. Forgejo Actions needs the `HARBOR_REGISTRY_USER` and
`HARBOR_REGISTRY_TOKEN` secrets to publish image updates to Harbor.

The image is intentionally built separately from the Terraform template. Push
and verify the image publication before changing the template's image digest;
this prevents a missing registry secret or failed build from breaking the
running workspace.

## Forgejo access

Each workspace uses Coder's managed SSH key through `coder gitssh`. The `t3code`
template configures this command as Git's global SSH command and prepares
`known_hosts` for the public Forgejo names. On its first start, copy the public
key printed in the startup log and add it to the Forgejo account, then retry the
clone from T3 Code:

```sh
GIT_SSH_COMMAND="coder gitssh" git clone --branch main \
  ssh://git@forgejo.forgejo.svc.cluster.local/Tom-Mendy/homelab.git \
  ~/project
```

No local private key or Forgejo token is stored in the workspace PVC or a
Kubernetes Secret. After changing a workspace template, publish it again with
the `coder templates push` command from the section above, then restart the
workspace so its startup script runs again.

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

## Hermes autonomous cluster administration

Hermes runs inside the cluster with the `hermes` service account, bound to
`cluster-admin` by `templates/hermes-rbac.yaml`. Its permissions cover all
namespaces, Secrets, RBAC, Pod execution and node operations. Restrict the
workspace template to its owner and administrators, and retain the Matrix
human allowlist. Users who can create arbitrary Pods in `coder-workspaces`
can also select this account and must be trusted administrators.

`KUBECONFIG=/opt/data/.kube/hermes.config` selects the internal Kubernetes API.
This file contains paths to the mounted CA and token, without credentials.
The projected token has a one-hour lifetime and Kubernetes renews it
independently of the operator's computer. The kubeconfig uses `tokenFile` so
clients pick up each renewal. See the
[Kubernetes service account documentation](https://kubernetes.io/docs/concepts/security/service-accounts/).

Startup installs checksum-pinned kubectl 1.34.12, Helm 3.22.0, Flux 2.9.5 and
jq 1.8.2 in the NFS-backed home. Cached clients survive Pod replacement without
another download. Update kubectl's minor version when the 1.34 control plane
changes. Coder and Crane remain available from the existing startup setup.

Startup enables the local terminal and full Hermes CLI toolset for Matrix and
cron, preserving a private backup of `config.yaml`. The installed
`homelab-cluster` skill explains cluster operations and storage policy. A
supervisor restarts the Matrix gateway after process exit. Stop the workspace
to shut it down intentionally; `hermes gateway stop` alone is temporary.

### Deployment and verification

Pushing this template to `main` triggers the existing Forgejo publication
workflow. `scripts/activate-hermes.py` then disables the owner's workspace
shutdown timer, updates and starts Hermes, waits for its agent, and checks
cluster-wide authorization plus a temporary ConfigMap create/read/delete.
No Kubernetes administrator credential passes through CI. The checks run
inside Hermes with its own projected token.

The publisher requires its existing `CODER_SESSION_TOKEN` Actions secret to
manage this workspace. For a manual activation after publishing the template:

```sh
coder login https://coder.tom-mendy.com
coder templates edit hermes-personal --private=true --default-ttl=0 --yes
coder schedule stop nainjoueur/hermes manual
coder update nainjoueur/hermes
coder start nainjoueur/hermes --yes
coder ssh nainjoueur/hermes -- 'bash -lc "
  kubectl auth whoami
  kubectl get nodes -o wide
  hermes gateway status
"'
```

Review existing Coder template permission grants. Disable any separately
configured mandatory restart or inactivity shutdown policy. The activation
check fails if the workspace still has a shutdown deadline. Coder's
[stop schedule](https://coder.com/docs/reference/cli/schedule_stop) applies on
the next build.

From the allowed Matrix account, ask Hermes to run `kubectl get nodes -o wide`.
Repeat after closing the operator's SSH session. Verify worker rescheduling
in a maintenance window from an independent administrator session; evicting
Hermes' own Pod would interrupt a drain command run from its terminal.

### Revocation and dependencies

Delete `ClusterRoleBinding/hermes-cluster-admin` to revoke permissions, and
remove its Git manifest so Flux does not recreate it. Stopping the workspace
removes its Pod and invalidates its token. Restoring the configuration backup
alone does not revoke permissions, and startup reapplies the terminal settings.

The cluster API, Synology NFS, a worker and the configured model provider must
remain available. Kubernetes access does not grant Forgejo push or host SSH
permissions. Use a separately authorized identity for those operations.

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
