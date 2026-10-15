# Restore Hermes Matrix encryption

The Hermes gateway repeatedly failed Matrix startup with `BAD_ACCOUNT_KEY`.
The token still authenticated as device `tbu5RoSQ3K`, and SQLite integrity checks
passed. The persisted Olm account opened with the key derived from the bot user
and that device ID, but failed with the `default` device suffix selected by the
installed adapter when `MATRIX_DEVICE_ID` was unset.

The Coder startup script now installs `launch-gateway.py`. Before each gateway
start, it calls Matrix `whoami`, validates the expected bot user and resolves the
token-bound device ID into `MATRIX_DEVICE_ID`. A failed lookup stops that attempt
and lets the existing supervisor retry. Tokens and response bodies are never
logged. No crypto database, device identity or recovery key was replaced.

Validate the launcher with `python3 scripts/test-hermes-matrix-identity.py` and
the template with Terraform formatting and validation. Publish `hermes-personal`
and update `nainjoueur/hermes` to apply it. Confirm encrypted startup succeeds,
then send a new message from Cinny and check reception and the Matrix reply.

The template was published and the workspace updated. The gateway verified
cross-signing with the existing recovery key, enabled E2EE and connected to
Matrix. A read-only replay successfully decrypted the latest encrypted user
message, timestamped `2026-10-12T17:17:07.717Z`, with the original crypto store.
Its contents were not logged. Historical missing-session warnings belong to an
older room with messages from August. A new Cinny message is still needed to
confirm the complete reception and reply path.

All five launcher tests and Terraform checks passed. The new report passes
Markdown checks; the repository-wide `rumdl check --fix .` still reports existing
violations in unrelated files.

The existing home and crypto store remain on the `nfs-k8s` PVC without worker
affinity. The storage policy check passes and active Kubernetes manifests contain
no `local-path` references.

When rotating a bot token, use `scripts/rotate-hermes-matrix-device.py` and follow
the existing Matrix recovery procedure. Do not delete the crypto store while
retaining the same Matrix device identity.
