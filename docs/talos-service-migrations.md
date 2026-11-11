# Remaining Talos service migrations

Execution continued on 2026-11-11. Application versions and optional-load
maintenance holds remain fixed. The migration branch is separate from main;
Ubuntu retains its original pinned Git source while each Talos revision is
reviewed and explicitly selected.

| Service | State | Data and routing |
| --- | --- | --- |
| Portfolio | Migrated and observed | Public Pangolin route to Talos .70 |
| Cinny | Migrated and observed | Public chat route to Talos .70; Matrix backend remains Ubuntu |
| Navidrome | Migrated and observed | Single writer on existing Synology paths; Ubuntu ingress bridge retained |
| SearXNG | Inert target prepared | Source VPN remains on Ubuntu; new Infisical identity requires administrator |

Cinny retained its exact image, configuration, and Matrix homeserver
`matrix.tom-mendy.com`. Public HTML and configuration hashes matched the
Talos copy, and Matrix discovery remained available. The public route uses
the existing Pangolin resource and Newt connector; resource ID 5 and its
existing default authentication policy ID 4 remain unchanged. The source
Cinny Deployment is stopped, while Tuwunel and Matrix RTC remain on Ubuntu.
The Matrix chart now records the separate frontend replica count for thaw.

A preliminary selectorless-Service bridge test exposed persistent upstream
connections that delayed routing rollback. The bridge was removed and the
original Service selector restored. A targets-only Pangolin blueprint then
exposed a compatibility problem: the existing connector/server combination
cleared the HTTP method and briefly returned 503. A full HTTP resource
definition restored the route. Future route changes on this installation must
include the full resource name, mode, domain, TLS setting, and HTTP target
method while preserving existing authentication settings. The valid direct
route was then rolled back to Ubuntu, returned to Talos, and observed for at
least five minutes after stopping Ubuntu Cinny. Both the homepage and config
and the upstream Matrix discovery endpoint passed throughout that window.

Navidrome's user state is SQLite on the approved Synology NFS export. Its
music library is the separate read-only `/volume1/music` export. The target
claims bind the same fixed existing paths with Retain and no node affinity.
The target Deployment must stay at zero replicas until the source writer is
stopped and a final native SQLite snapshot is verified. Generated cover and
transcode caches are recoverable from the pre-cutover file snapshot; user and
playlist state must come from the final stopped-writer database snapshot.
Never run both clusters' Navidrome writers against the shared data directory.

Private evidence and per-service recovery scripts are outside Git:

```text
~/.local/state/homelab/talos-migration/20261111-remaining-services/
```

Application RBAC and manifests are under `talos/bootstrap` and
`talos/gitops/apps`. No credential-bearing Secret is committed. Imported local
TLS Secrets need renewal or replacement by the final target certificate
controller before their recorded expiry; public TLS remains Pangolin-managed.
Do not resume an Ubuntu release or component marked retired during a bulk thaw.

Navidrome completed 305.3 seconds of observation with 30 healthy samples.
Its final stopped-writer SQLite snapshot restored successfully, all 48 table
counts matched, and the running target preserved user, playlist, and share
fingerprints. The full pre-cutover file archive was decrypted and extracted,
with SQLite integrity checked. The target read the existing music export as
the application UID before source shutdown. No database or library path was
replaced by a new empty volume.

The first stopped-writer backup attempt could not create SQLite WAL metadata
through the read-only inspection mount. The source was automatically restored
and remained the only writer. The corrected attempt copied the quiesced
SQLite files into writable temporary recovery space, then took and verified a
native backup there before activating Talos. No manual source database edits
were made. The incomplete initial file-transfer artifact and plaintext restore
checks were removed after the verified encrypted backups were available.

The next step is blocked by a confirmed Infisical administration permission,
not Talos connectivity. See the
[administrator handoff](talos-infisical-admin-handoff.md). The target operator
and reviewer are prepared, and TokenReview from the current Infisical server
to Talos passed with CA verification. SearXNG remains on Ubuntu until its new
Talos identity is authorized. Do not boot node3 into an installer yet.
