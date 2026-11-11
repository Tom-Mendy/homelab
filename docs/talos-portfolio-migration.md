# Portfolio migration to Talos

Cut over on 2026-11-11. Portfolio runs on Talos node2 with the unchanged image:

```text
harbor.home.tom-mendy.com/portfolio/portfolio:latest@sha256:08333a8094b51d51ff777e6dff3ffdabfa89e859a8da88b95d9f6f85ea778b38
```

The application is static and has no PVC, database, jobs, or writable user
state. Its immutable image is the application artifact; no database or live
filesystem transfer was required. The source Deployment, Service, Ingress,
EndpointSlice, Pod image ID, registry credential, and relevant routing state
were captured privately before changes.

The dedicated [Talos application directory](../talos/gitops/apps/portfolio/)
contains a Deployment, Service, HTTP Ingress, HTTPS Ingress, and route-proof
Middleware. It preserves the Ubuntu container security settings and resource
requests. One replica runs on node2. The
[application reconciler](../talos/bootstrap/portfolio-reconciler.yaml) can
manage these resource types only in namespace `portfolio`. Read-only Pod and
ReplicaSet permissions allow Flux's Deployment health assessment. It cannot
read Secrets or create Pods directly. The original validation reconciler was
not granted application permissions.

The inherited Harbor credential was found to permit push and delete. It was
replaced on Talos by project-scoped robot ID 513, `talos-portfolio-pull`.
Registry authorization granted only pull even when push and delete were
requested, and the robot retrieved the exact pinned manifest. The original CI
credential was left unchanged. The new credential exists only in the Talos
Portfolio Secret and private recovery material.

The selected application certificate was imported into Secret
`portfolio/portfolio-tls`; the full Ubuntu ACME account and other certificate
keys were not retained in this operation's export. Neither Secret is in Git.
The imported local-ingress certificate expires on 2027-01-26 and does not
renew automatically on Talos. Renew that Secret before expiry or replace it
with the target certificate automation. Public TLS is independently managed
and renewed by Pangolin's existing Let's Encrypt resolver.

Five paths, including both language pages and Astro assets, returned identical
status, body hashes, lengths, and redirects through Ubuntu and Talos. Talos
HTTP and HTTPS passed, including normal certificate and hostname verification.
The Ubuntu Newt Pod could reach the Talos ingress and received the expected
page hash. Flux reported the target Deployment healthy with the same image
content. The temporary response header `X-Migration-Route: talos-portfolio`
identifies the tested target route; remove its Middleware and annotations in a
reviewed follow-up after migration observation no longer needs that marker.

Public access was already broken before cutover. DNS pointed to the existing
Pangolin VPS, which returned a default self-signed certificate and HTTP 404.
Read-only inspection found no `tom-mendy.com` resource in Pangolin's database
or generated Traefik configuration. This was not a disabled resource.
A consistent SQLite backup passed quick_check and a transfer SHA check.
No direct database edits were used to repair routing.

The existing Newt blueprint first restored Portfolio's documented Ubuntu
Service target. Public certificate verification and content checks then
passed. Only the new Portfolio resource was subsequently switched to Talos:

```text
Browser -> Pangolin HTTPS -> existing Ubuntu Newt tunnel -> 10.0.0.70:80
        -> Talos Traefik -> Talos Portfolio Service -> Portfolio Pod
```

The root page redirects to the same language path as before. HTTP on the
public endpoint redirects to HTTPS. The public IP and DNS record did not
change. Pangolin continues terminating public TLS. The tunnel and backend
HTTP method match the existing routing model; no unverified TLS mode is used
for public health checks.

The [Newt values](../kubernetes/newt/upstream-values.yaml) record this target.
Newt watched the projected blueprint update and applied it without a Pod
restart. The existing 18 Pangolin HTTP routers were compared before and after
and remained unchanged; only Portfolio routers were added. Existing media
blueprint entries were preserved.

Routing rollback to the Ubuntu Service was rehearsed successfully before the
old Pod was stopped. Traffic was then switched back to Talos and the old
Deployment scaled to zero. The Ubuntu Helm release remains suspended; its
persistent suspension is recorded in the Ubuntu Flux manifest and the
[retirement list](../talos/retired-ubuntu-applications.json). Keep this release
out of any bulk maintenance thaw. The original global freeze baseline remains
unchanged, so merge the reviewed migration changes before selecting a new
Ubuntu Git revision for thaw.

Private evidence and standalone rollback scripts are stored here:

```text
~/.local/state/homelab/talos-migration/20261111-portfolio/
```

To roll back after the old Pod has stopped:

1. Keep Talos serving traffic while scaling Ubuntu Deployment
   `portfolio/portfolio` to its captured original replica count.
2. Wait for the Ubuntu Deployment and its Service endpoints to become ready.
3. Change only the Portfolio blueprint target to
   `portfolio.portfolio.svc.cluster.local:80`, keeping method HTTP and host
   header `tom-mendy.com`. Preserve all other resources in the blueprint.
4. Wait for Newt's live reload, then verify normal public TLS and the expected
   page hash. The Talos route marker must be absent.
5. Suspend the Talos `portfolio` Kustomization if rollback will be retained.
   Leave its resources intact while investigating.

The private `rollback.py` implements the startup-before-routing sequence with
separate explicit Ubuntu and Talos access files. It uses Python standard-library
helpers and refuses to overwrite a blueprint that has changed since migration,
so later route additions must be merged manually. Its credentials remain
outside Git. The routing rehearsal did not require replaying database writes,
because Portfolio has no mutable application state.

Portfolio still depends on Ubuntu-hosted Newt and Harbor. The GitOps source
also uses the temporary Ubuntu Forgejo SSH bridge. These are remaining
infrastructure dependencies, not application Pods on Ubuntu. Do not retire
node3 or remove the shared tunnel before those dependencies are migrated.
No other application was cut over during this operation.

The deployed GitOps code is pinned to commit
`9273724c467bf284440b9772b3c06f46e3804682` on the separate migration branch.
The Ubuntu root source remains pinned to its original maintenance baseline.

The final observation passed for 606.8 seconds, from 12:58:27 to 13:08:33 UTC
on 2026-11-11. All 58 public HTTPS/content checks were healthy, the Talos route
marker was present, and the target Pod remained Ready with zero restarts.
The Ubuntu Deployment remained stopped. The dedicated pull-only credential
also passed an isolated fresh image-pull test, and its test Pod was removed.

The public certificate was verified through 2027-02-09. The existing 18 other
Pangolin routers remained unchanged, and the shared Newt Pod did not restart.
Final checks also confirmed the six Ubuntu databases and core recovery
services healthy. The migration archive contains the consistent pre-change
Pangolin backup, application access and TLS material, the branch Git bundle,
and rollback scripts. It must remain private and encrypted.
