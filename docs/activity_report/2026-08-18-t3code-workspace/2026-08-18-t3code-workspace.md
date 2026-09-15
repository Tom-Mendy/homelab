# Create a dedicated T3 Code workspace

## Problem

T3 Code failed inside the generic Coder `Agent Workspace` because its global
`node-pty` package had no Linux native `pty.node` file. The fix must not modify
the user's dotfiles or affect existing workspaces.

Workspace creation also showed that a bootstrap-generated local SSH key was not
accepted by Forgejo. Coder already provides a managed key through `coder
gitssh`, so the templates must use that key instead.

## Investigation

The workspace template was inspected with:

```sh
rg -n -i 't3|node-pty|workspace|image' kubernetes/coder
sed -n '1,220p' kubernetes/coder/workspace-templates/agent-workspace/main.tf
```

The existing template uses the generic `codercom/example-universal` image and
does not install or build T3. The selected fix is therefore a separate Coder
template with an isolated startup script.

Workspace logs also showed:

```text
git@forgejo.forgejo.svc.cluster.local: Permission denied (publickey).
Encountered an error running "coder gitssh"
```

The bootstrap was generating `~/.ssh/id_ed25519`, while Coder was advertising a
different managed key. That local key could not authenticate to Forgejo.

## Changes

The new `t3code` template:

- keeps the existing `codercom/example-universal` image;
- installs T3 with `npm_config_build_from_source=true`;
- loads `node-pty` and spawns a shell as a startup smoke test;
- stores its home on an NFS-backed `nfs-k8s` PVC;
- uses Coder's managed SSH key for Forgejo clones;
- leaves `agent-workspace` and external dotfiles unchanged.

## Validation

The following checks were run after the change:

```sh
terraform -chdir=kubernetes/coder/workspace-templates/t3code fmt -check
terraform -chdir=kubernetes/coder/workspace-templates/t3code init -backend=false
terraform -chdir=kubernetes/coder/workspace-templates/t3code validate
helm lint kubernetes/coder
./scripts/check-storage-policy.sh
rumdl check --fix kubernetes/coder docs/activity_report/2026-08-18-t3code-workspace
```

The first Terraform initialization attempt failed because the restricted
environment could not resolve `registry.terraform.io`. Re-running initialization
with network access downloaded the locked providers and both templates then
returned `Success! The configuration is valid.`

Runtime verification after publishing the template:

```sh
coder templates push t3code \
  --directory kubernetes/coder/workspace-templates/t3code
coder create t3code
coder ssh t3code -- node -e 'require("node-pty").spawn("sh").kill()'
```

## Outcome

T3 now has a dedicated workspace boundary. Its Linux `node-pty` native module
is built during startup, while the generic `Agent Workspace` remains unchanged.
