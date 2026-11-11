# Infisical administrator handoff for Talos

The organization administrator step was completed through the Infisical web
interface on 2026-11-11. A separate `talos-searxng` identity was created with
No Access at organization scope and Viewer access to project `homelab`. Its
Kubernetes authentication points at the Talos API. The existing Ubuntu identity
and authentication configuration remain unchanged. The new identity ID is
stored privately with the migration recovery files.

Talos preparation is complete: the same Infisical operator v0.11.16 is running,
pinned to the observed image digest. A dedicated reviewer ServiceAccount has
only permission to create TokenReviews. A token from the Talos SearXNG sync
ServiceAccount was successfully reviewed from the running Ubuntu Infisical
server against the Talos API, with normal TLS and CA verification. Network
reachability, certificate trust, and reviewer permission are therefore tested.

The completed configuration is recorded here for recovery. The interface
sequence followed the
[official Kubernetes authentication guide](https://infisical.com/docs/documentation/platform/identities/kubernetes-auth).

1. Create `talos-searxng` with the No Access organization role. Keep the Ubuntu
   identity separate.
2. Configure the Kubernetes authentication settings below, targeting the
   Talos API.
3. Add the identity to project `homelab` as Viewer. The sync selects `prod`,
   `/searxng`.

| Setting | Required value |
| --- | --- |
| Kubernetes API | `https://talos-api.home.tom-mendy.com:6443` |
| Review method | API using a reviewer token |
| TLS verification | Enabled |
| Allowed namespace | `searxng` |
| Allowed ServiceAccount | `searxng-infisical-sync` |
| Optional audience restriction | Leave empty for the current operator setup |
| Token TTL | 3600 seconds |
| Token maximum TTL | 86400 seconds |
| Token uses limit | 0 |

The CA and reviewer token are prepared locally, not in Git:

```text
~/.local/state/homelab/talos-migration/20261111-remaining-services/infisical/
  talos-kubernetes-ca.crt
  talos-reviewer.jwt
  talos-searxng-kubernetes-auth.private.json
```

The JSON file combines the fields for an administrator-driven API operation;
the PEM and JWT files supply the corresponding interface fields. Keep the JWT
private. The organization ID is `77a7a5c7-93ee-4cc0-9982-732776db031c` and the
project ID is `758123bc-7eaa-4256-98a2-bb7438a783b8`.

The identity ID was installed in the Talos
`searxng/searxng-infisical-identity` Secret, and the resources from
`talos/bootstrap/pending/searxng-secret-sync.json` were applied. Infisical
connection, authentication, and static-secret reconciliation all report
success. The two synchronized application Secrets match the Ubuntu values.

SearXNG now runs on Talos. The Ubuntu VPN writer was stopped before the Talos
sidecar started; the quiesced Nym state has an encrypted, verified private
archive. Talos reports a connected VPN and Swiss egress. The existing LAN
Ingress forwards to Talos through a temporary Ubuntu bridge, and the source
Deployment and HelmRelease remain stopped/suspended.

Cinny and Navidrome are migrated and observed. Portfolio remains healthy on
Talos. The six singleton PostgreSQL clusters, recovery services, and remaining
applications stay on Ubuntu. No additional machine was rebooted or erased in
this continuation, and node3 is not yet ready for installation.
