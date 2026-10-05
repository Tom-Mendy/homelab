# Synology DSM login through Authentik

DSM uses native OIDC at `https://nainjoueur.synology.me:5001/`. Flux loads
`kubernetes/authentik/blueprints/95-synology.yaml`. Authentik permits
`homelab-admins` and `synology-users`; DSM keeps its own account permissions.
SSO does not create DSM accounts or grant DSM administrator rights.

Local DSM accounts require DSM 7.2 or later. DSM 7.1 requires a shared LDAP
directory for OIDC login; creating a local account does not enable SSO on that
version. After upgrading, select `Domain/LDAP/local` under **Account type**.

Before deploying the change:

1. In Infisical, open the `homelab` project, `prod` environment, `/oidc` path.
   Add `SYNOLOGY_OIDC_CLIENT_SECRET` with an independent random secret from a
   password manager. Keep it out of Git and shell history.
2. In Authentik, confirm `Synology DSM RSA` exists and uses RSA. If absent,
   open **System > Certificates > Generate** and create a
   certificate-key pair named `Synology DSM RSA`, with private key algorithm
   `RSA`. The self-signed certificate is for token signing, not DSM HTTPS.
3. Confirm the intended users already have enabled DSM accounts. In Authentik,
   each user's username must match their DSM account name. If it differs, set
   the user's attribute `synology_username` to the existing DSM account name.
   Grant access through `synology-users` or `homelab-admins` and ensure each
   user has an email address for the provider's subject claim.

After the change reaches the Flux source, reconcile and wait for secret sync:

```bash
flux reconcile kustomization flux-system -n flux-system --with-source
kubectl -n authentik wait infisicalstaticsecret/authentik-oidc \
  --for=condition=secrets.infisical.com/LastReconcileStatus --timeout=5m
```

Confirm `authentik-oidc` contains a non-empty `SYNOLOGY_OIDC_CLIENT_SECRET`
without printing it. Restart the Authentik server and worker if the secret
reload controller has not already done so. Environment variables update only
when the containers restart.

```bash
kubectl -n authentik rollout restart deployment/authentik-server \
  deployment/authentik-worker
kubectl -n authentik rollout status deployment/authentik-server
kubectl -n authentik rollout status deployment/authentik-worker
kubectl -n authentik exec deployment/authentik-worker -- \
  ak apply_blueprint /blueprints/mounted/cm-authentik-oidc-blueprint/95-synology.yaml
```

The Synology blueprint requires both the secret and RSA key before it can
apply. Other applications have separate blueprint files. Check the Synology
provider in Authentik and its discovery URL before enabling DSM SSO.
`id_token_signing_alg_values_supported` must contain `RS256`.

In DSM, open **Control Panel > Domain/LDAP > SSO Client**. Enable the OpenID
Connect SSO service, open its settings, and enter these values:

| Setting | Value |
| --- | --- |
| Profile | `OIDC` |
| Account type | `Domain/LDAP/local` |
| Name | `Authentik` |
| Well Known URL | `https://authentik.home.tom-mendy.com/application/o/synology/.well-known/openid-configuration` |
| Application ID | `synology` |
| Application Key | Value of `SYNOLOGY_OIDC_CLIENT_SECRET` from Infisical |
| Redirect URI | `https://nainjoueur.synology.me:5001` |
| Authorization Scope | `openid profile email` |
| Username Claim | `preferred_username` |

Save the settings. Keep password login available and leave **Select SSO by
default on the login page** disabled until verification passes. DSM and the
browser must both reach and trust the Authentik HTTPS endpoint.

Use a private browser window, allow pop-ups for DSM, and sign in through
Authentik. Verify the expected DSM username and permissions. Test an allowed
non-admin account and an account outside both Authentik access groups. Confirm
the latter cannot authenticate to this application. Finally, test direct local
administrator login while Authentik is unavailable.

If DSM reports an invalid account, check the `preferred_username` claim against
the existing DSM account. For `not privilege`, check pop-up blocking and the
redirect URI. Use the exact origin above, without a trailing slash or
`#/signin`. A future DSM hostname change must update both the blueprint and
DSM's redirect URI. Use one canonical DSM origin.

If DSM cannot obtain information about the SSO server, check the discovery URL
before changing certificates or credentials:

```bash
curl --fail --show-error --max-time 15 \
  https://authentik.home.tom-mendy.com/application/o/synology/.well-known/openid-configuration
kubectl -n authentik get pods -o wide
```

HTTP 503 means the ingress has no available Authentik server. Check server
readiness and logs. A NAS restart also interrupts Authentik's NFS-backed
PostgreSQL storage, so confirm database recovery before retrying SSO.

After the 2026-10-04 upgrade to DSM 7.4.1-90080, PostgreSQL on `node3`
experienced slow NFSv4.1 file opens. Authentik health checks exceeded their
three-second timeout and the ingress returned HTTP 503. NFS SEQUENCE replies
persistently carried `SEQ4_STATUS_RECALLABLE_STATE_REVOKED` on `node3`, while
`node2` had normal latency. NFSv3 provided temporary recovery.

Draining `node3` and closing every Synology NFS mount reset its stale client
state. The same 192-operation file-open benchmark then completed in 0.066
seconds, with 0.422 ms p95 latency. The Authentik PostgreSQL PV
`pvc-838dd586-f332-46ea-b676-84a72bbad01b` was restored to
`mountOptions: [nfsvers=4.1]`. PostgreSQL recovered on `node3`, and discovery
and health endpoints returned HTTP 200. The database retains no node placement
restriction; both workers use the shared `nfs-k8s` storage class.

After the subsequent operator-initiated node updates and reboots, all three
nodes returned Ready with kernel `6.8.0-142-generic`. PostgreSQL's actual mount
remained NFSv4.1. The scratch-volume benchmark passed on both workers with p95
latency below 1 ms, all six CloudNativePG clusters were healthy, and Authentik
discovery and readiness returned HTTP 200.

For rollback, sign in with the local DSM administrator and disable **Enable
OpenID Connect SSO service**. Keep that account and its credentials available
outside Authentik. NFS storage and file-sharing credentials are independent
of this browser login integration.

References: [Authentik Synology integration](https://integrations.goauthentik.io/infrastructure/synology-dsm/)
and [DSM SSO client documentation](https://kb.synology.com/en-us/DSM/help/DSM/AdminCenter/file_directory_service_sso?version=7).
