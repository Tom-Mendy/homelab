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
| SearXNG | Migrated and observed | NymVPN state kept on the same Synology NFS path; Ubuntu ingress and in-cluster consumer bridges reach Talos .70 |

SearXNG now runs on Talos with the same application and NymVPN image digests.
The source Deployment was stopped before the Talos writer started. A read-only
inspection Pod captured the quiesced VPN state (13 files, 245,574 bytes) into
an encrypted Age archive; decryption and gzip/tar integrity checks passed in
memory. Infisical now authenticates the dedicated Talos ServiceAccount through
the Talos API with CA verification, and both synchronized application Secrets
match Ubuntu. NymVPN reports Connected and the application reports Swiss
egress. The unchanged LAN hostname reaches Talos through an Ubuntu
Service/EndpointSlice bridge from Traefik .60 to Talos ingress .70. Direct and
bridged HTTPS, health, route marker, and response body matched during 313
seconds of observation (31 samples). One request immediately after the
Ingress backend patch returned 503 while routing updated; subsequent checks
and the full observation window passed. Ubuntu SearXNG remains at zero
replicas and its HelmRelease remains suspended.

OpenWebUI in the Ubuntu `ollama` namespace still uses the cluster-local URL
`http://searxng.searxng.svc.cluster.local:8080/search`. After the SearXNG
cutover, that URL failed because Kubernetes Service DNS is cluster-scoped. The
Ubuntu Service now has no selector and an EndpointSlice targets Talos ingress
`.70:80`; a second Talos Ingress host rule accepts the unchanged service FQDN.
The actual OpenWebUI pod returned HTTP 200 JSON from its configured URL after
the bridge. Keep this bridge until OpenWebUI moves, then remove the Ubuntu
selectorless Service/EndpointSlice and the internal Talos host rule in the same
reviewed Git change. The original Ubuntu Service selector and port are in the
private rollback snapshot `searxng/source-service-before-internal-bridge.json`.

To roll back, suspend the Talos SearXNG Kustomization and stop its Deployment,
then wait until its Pod is gone before starting the Ubuntu Deployment against
the shared NFS path. Restore the Ubuntu Ingress backend to its original
`searxng` Service only after Ubuntu VPN connectivity and health pass. Do not
restore the older pre-cutover archive over state written by Talos; both
clusters use the same NFS directory.

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

The Infisical administrator action is complete; its identity and Kubernetes
authentication settings are recorded in the
[administrator handoff](talos-infisical-admin-handoff.md). Continue with the
next application individually. Do not boot node3 into an installer yet.
