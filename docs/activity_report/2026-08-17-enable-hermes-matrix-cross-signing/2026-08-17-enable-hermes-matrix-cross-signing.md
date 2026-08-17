# Enable Durable Matrix Cross-Signing for Hermes

Date: 2026-08-17

## Problem

Hermes joined the encrypted direct room as
`@hermes-bot:matrix.tom-mendy.com`, but it could not decrypt messages from
Cinny. All failed events referenced the same missing Megolm session, and the
gateway warned that device `PMWUwNWowi` was not cross-signed.

## Reasoning and commands

Read-only Matrix API checks showed one encrypted room containing Tom and the
bot. The bot joined before the failed messages, but Cinny did not share the
room session. Hermes' official Matrix guidance explains that clients can refuse
to share encryption sessions after device changes when the bot device is not
cross-signed. The durable fix is a recovery key, not another access token or a
plain-text room.

The first bootstrap attempt failed to create a key. Its log exposed a template
regression:

```text
MATRIX_DEVICE_ID=HERMES_BOT
Matrix: failed to create optional E2EE client: BAD_ACCOUNT_KEY
```

The workspace had restarted on an older Coder template. Its forced device ID
changed the crypto-store pickle key, while `crypto.db` had been created by the
corrected configuration. The gateway was stopped, the current repository
template was republished, and `coder update nainjoueur/hermes` removed the
forced variable. The existing crypto database was deliberately preserved.

The bootstrap was then repeated with a temporary output file:

```bash
hermes gateway stop
MATRIX_RECOVERY_KEY_OUTPUT_FILE=/tmp/hermes-matrix-recovery-key \
  hermes gateway run
```

Hermes reported that cross-signing was bootstrapped. The generated file is 60
bytes and mode `0600`; its value was never printed. It must be copied to
Infisical as `/matrix/HERMES_MATRIX_RECOVERY_KEY` before the final rollout.

The GitOps change maps that Infisical value into the existing `hermes-matrix`
Secret and injects it as `MATRIX_RECOVERY_KEY`. E2EE changes from `optional` to
`required`, preventing an unnoticed fallback to unencrypted operation.

Validation commands:

```bash
helm lint kubernetes/matrix
helm template matrix kubernetes/matrix >/tmp/matrix-rendered.yaml
terraform fmt -check kubernetes/coder/workspace-templates/hermes-personal/main.tf
./scripts/check-storage-policy.sh
rumdl check --fix .
```

The direct `kubeconform` validation attempt could not run because the binary
was no longer installed in the administration host's `PATH`:

```text
zsh: command not found: kubeconform
```

The repository's `scripts/test-helm-chart.sh` was used instead. All 24 active
charts passed both `helm lint` and `helm template`, including Matrix. Terraform
formatting and validation passed, the storage policy returned
`storage policy ok`, and no active `local-path` reference was found.

After the operator stored the key in Infisical, Matrix chart revision 9 was
deployed. `InfisicalStaticSecret/hermes-matrix` reported successful
reconciliation, and a key-name-only check showed:

```text
MATRIX_ACCESS_TOKEN
MATRIX_ALLOWED_USERS
MATRIX_RECOVERY_KEY
```

An initial attempt to list those names with a JSONPath `range` failed because
this kubectl JSONPath implementation rejected the comma in the variable list.
The equivalent read-only `jq` query succeeded without exposing any value.

## Outcome

Cross-signing is bootstrapped, and the recovery key now comes exclusively from
Infisical. Coder template version `handsome_knight42` is active, the workspace
is healthy and current, `MATRIX_E2EE_MODE` is `required`, and the gateway is
running. The temporary recovery-key file disappeared when Coder replaced the
old pod; it was never stored on the NFS PVC.

Two post-rollout starts found the Matrix master key, self-signing key, and two
signatures on device `PMWUwNWowi`. Neither start logged a cross-signing warning,
`BAD_ACCOUNT_KEY`, nor an E2EE initialization failure.

Four messages from the previous Megolm session remain undecryptable, as
expected: Cinny created that session before trusting the corrected bot device.

## Follow-up: stale device identity

A message sent from Cinny in a newly created encrypted room still failed with a
new Megolm session:

```text
Failed to decrypt megolm event: no session with given ID
Jp85MVjei+Wb15qYs/9h0ScPqPeN3A3HSMob/ze14J4 found
```

The server had 50 signed Curve25519 one-time keys for the bot, so key exhaustion
was excluded. The local crypto database had previously been deleted while the
access token, and therefore its Matrix device ID, was retained. Other Matrix
clients can cache the old keys for that device ID and refuse to establish the
new Olm session.

Tuwunel's native admin-login endpoint creates a fresh visible device while
minting an access token. `scripts/rotate-hermes-matrix-device.py` wraps that
endpoint through the existing localhost port-forward. It reads and writes only
mode-0600 token files, validates the returned identity through `whoami`, and
never prints either token. The recovery key remains unchanged; only the access
token and local Hermes crypto store need rotation.
