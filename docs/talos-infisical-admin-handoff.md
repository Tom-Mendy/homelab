# Infisical administrator handoff for Talos

Migration paused at the first operation requiring organization administration.
The existing SearXNG identity authenticates successfully and can read its own
Kubernetes configuration, but an update using the same unchanged TTL returned
HTTP 403. Its organization role is No Access and its project role is Viewer.
A read-only organization-role audit found that all existing machine identities
have No Access at organization scope. No administrator API credential is
available in the current environment.
The existing Ubuntu authentication configuration was not changed.

Talos preparation is complete: the same Infisical operator v0.11.16 is running,
pinned to the observed image digest. A dedicated reviewer ServiceAccount has
only permission to create TokenReviews. A token from the Talos SearXNG sync
ServiceAccount was successfully reviewed from the running Ubuntu Infisical
server against the Talos API, with normal TLS and CA verification. Network
reachability, certificate trust, and reviewer permission are therefore tested.

An organization administrator must create a separate identity for Talos.
Use the existing [Infisical instance](https://infisical.home.tom-mendy.com).
The interface sequence follows the
[official Kubernetes authentication guide](https://infisical.com/docs/documentation/platform/identities/kubernetes-auth).

1. In the organization's identity controls, create `talos-searxng` with the
   No Access organization role. Keep the Ubuntu identity unchanged.
2. Configure the new identity to authenticate with Kubernetes, using the
   settings below. These settings select Talos rather than the Ubuntu API.
3. In project `homelab`, add the new identity with the same Viewer role as the
   existing SearXNG identity. This preserves the existing read-only project
   permission model. The prepared sync resource selects `prod`, `/searxng`.
4. Return only the new identity ID. It is an identifier, not an authentication
   credential. Do not send the reviewer JWT or any API token in chat.

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

After the identity exists, the agent can install its ID in the Talos
`searxng/searxng-infisical-identity` reference, apply the prepared
`talos/bootstrap/pending/searxng-secret-sync.json`, and verify authentication
and both synchronized application Secrets. This pending file has deliberately
not been applied with the old Ubuntu identity ID.

SearXNG continues serving on Ubuntu with its VPN connected and a checked
Swiss exit. Its Talos Deployment remains at zero replicas. TUN availability,
image pull, same-image staging, NFS binding, copied bootstrap Secrets, and the
Talos Pod-CIDR adjustment are prepared. No second VPN daemon has been started.
Only after secret synchronization is verified should the source VPN writer be
stopped, its state backed up, and the Talos daemon activated. Then verify VPN
connectivity and Swiss egress before redirecting requests.

Cinny and Navidrome are migrated and observed. Portfolio remains healthy on
Talos. The six singleton PostgreSQL clusters, recovery services, and remaining
applications stay on Ubuntu. No additional machine was rebooted or erased in
this continuation, and node3 is not yet ready for installation.
