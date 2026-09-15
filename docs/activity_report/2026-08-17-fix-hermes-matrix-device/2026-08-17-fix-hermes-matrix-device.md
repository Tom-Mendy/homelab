# Fix the Hermes Matrix Device Identity

Date: 2026-08-17

## Problem

The Hermes gateway could authenticate its Matrix access token, but E2EE startup
failed with `Device ID in keys uploaded does not match your own device ID`.
Consequently, Matrix remained queued for retry and the gateway had no connected
messaging platform.

## Reasoning and commands

The workspace environment and Hermes Matrix adapter were inspected without
printing the access token. The template forced `MATRIX_DEVICE_ID=HERMES_BOT`,
while Matrix's authenticated `whoami` response identified the token as:

```text
user_id:   @hermes-bot:matrix.tom-mendy.com
device_id: PMWUwNWowi
```

The server listed only that generated device, and the account had not joined
any rooms. Hermes prefers a configured device ID over the value returned by
`whoami`, so it attempted to upload keys for `HERMES_BOT` with a token bound to
`PMWUwNWowi`. The server correctly rejected the mismatch.

The adapter already learns the stable device ID from the access token. The
minimal durable fix is therefore to remove `MATRIX_DEVICE_ID` from the Coder
template instead of copying the current generated value into Git. This also
keeps future access-token rotation working without another template edit.

The existing local crypto database was created under the incorrect identity
and must be removed while the gateway is stopped. It contains only generated
E2EE state; removing it does not delete the Matrix account, access token, rooms,
or message history.

Validation and rollout commands:

```bash
terraform fmt -check kubernetes/coder/workspace-templates/hermes-personal/main.tf
./scripts/check-storage-policy.sh
rg -n 'storageClassName: local-path|storage_class_name\s*=\s*"local-path"' kubernetes
rumdl check --fix .

coder templates push hermes-personal \
  --directory kubernetes/coder/workspace-templates/hermes-personal \
  --message "Fix Hermes Matrix device identity" --yes
hermes gateway stop
rm /opt/data/platforms/matrix/store/crypto.db
coder update nainjoueur/hermes
```

The first Terraform validation failed before publication because the local
provider cache was absent:

```text
Error: missing or corrupted provider plugins:
- registry.terraform.io/coder/coder 2.18.0
- registry.terraform.io/hashicorp/kubernetes 3.2.1
```

Running `terraform init -backend=false -input=false` downloaded the versions
already pinned in `.terraform.lock.hcl`. The subsequent validation returned
`Success! The configuration is valid.` The generated `.terraform` cache was
moved out of the repository after validation.

The template publication completed successfully and activated version
`silly_herman74`. Two non-interactive update attempts failed safely before
making changes because Coder 2.28.6 does not accept `--yes` for `update`:

```text
coder update nainjoueur/hermes --yes
parsing flags: unknown flag: --yes

coder --yes update nainjoueur/hermes
parsing flags: unknown flag: --yes
```

Running `coder update nainjoueur/hermes` interactively updated the workspace.
`coder restart nainjoueur/hermes --yes` then performed a second clean restart
to verify that the new E2EE state survived pod replacement.

The old 92 KiB `crypto.db` was removed after checking its exact path. The
gateway had already stopped, so `hermes gateway stop` reported that no process
needed to be terminated.

## Outcome

The workspace is running and healthy on the active template. Its PVC remains
bound to `nfs-k8s`, so the workspace data is not tied to the worker hosting the
current pod.

After both starts, `MATRIX_DEVICE_ID` was absent and Matrix resolved the device
from the token as `PMWUwNWowi`. The server now exposes both expected public
device keys:

```text
curve25519:PMWUwNWowi
ed25519:PMWUwNWowi
```

`hermes gateway status` reports a running gateway. The original device mismatch
does not appear in either post-fix log. The remaining warning says the device
is not cross-signed; this does not prevent the gateway from connecting or using
its persisted E2EE keys.

The repository checks returned `storage policy ok`, found no active
`local-path` reference, and found no whitespace errors in the final diff. The
live Deployment has neither a node selector nor affinity, and its 20 GiB PVC is
bound to `nfs-k8s`; it can therefore be recreated on either worker without
stranding its persistent data. A first attempt to query the Deployment affinity
over SSH failed with `kubectl: not found` because the Hermes container does not
ship cluster administration tools. Running the same read-only query from the
administration host returned empty node-selector and affinity fields.

The required global `rumdl check --fix .` exposed 313 pre-existing Markdown
issues across the repository and automatically fixed 180 issues in six older
files. Those unrelated formatter edits were removed from this task. A targeted
check of this activity report completed with `Success: No issues found`.

The bot currently has no joined rooms. The Cinny conversation shown during the
incident invited `@hermes:matrix.tom-mendy.com`, but the configured bot is
`@hermes-bot:matrix.tom-mendy.com`. The operator must create a new direct chat
with the exact bot ID. Hermes will accept it when the inviter is present in
`MATRIX_ALLOWED_USERS`; the live allowlist contains
`@tom:matrix.tom-mendy.com`. Direct messages do not require an explicit mention.
