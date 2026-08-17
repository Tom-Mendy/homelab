# Matrix Operations

This chart deploys a federated Tuwunel homeserver, Cinny, and the Element
MatrixRTC backend. Matrix IDs use `@user:matrix.tom-mendy.com`. Human accounts
authenticate through Authentik; `hermes-bot` is the only local account.

## Before the first Flux reconciliation

1. In Infisical project `homelab`, environment `prod`, create:
   - `/oidc/MATRIX_OIDC_CLIENT_SECRET`: a random 32-byte value.
   - `/matrix/MATRIX_REGISTRATION_SHARED_SECRET`: a random 32-byte value.
   - `/matrix/LIVEKIT_KEY`: a random 20-character alphanumeric value.
   - `/matrix/LIVEKIT_SECRET`: a random 64-character alphanumeric value.
2. The dedicated Infisical identity is `matrix-k8s-auth`. It must allow the
   `matrix/matrix-infisical-sync` ServiceAccount and have read access to
   `/matrix`. The existing Authentik identity only distributes the OIDC secret
   from `/oidc`.
3. Add public DNS records for `matrix.tom-mendy.com`, `chat.tom-mendy.com`, and
   `rtc.tom-mendy.com`, all pointing to the Pangolin VPS (`72.61.113.235`).
4. In Pangolin, create HTTPS resources for those three hostnames and forward
   them through Newt to Traefik. Do not add an internal Blocky override for
   `rtc.tom-mendy.com`: clients must resolve its public media IP.
5. Enable Pangolin raw resources and expose the following directly to
   `matrix-rtc.matrix.svc.cluster.local`:
   - TCP `7881`.
   - UDP `50100` through `50110`, one raw resource per port.

Allow the same ports in the VPS firewall and Pangolin's Docker/Traefik
entrypoints. The eleven-port UDP range is intentionally sized for a small
homelab; widen the range in the chart and Pangolin together if calls exhaust it.

## Deploy and verify

Commit and push the repository changes, then reconcile Flux:

```bash
flux reconcile source git flux-system
flux reconcile helmrelease authentik-extras -n flux-system --with-source
flux reconcile helmrelease matrix -n flux-system --with-source
kubectl get pods,pvc,ingress -n matrix
kubectl get infisicalstaticsecret -n authentik matrix-runtime
```

Verify public discovery and federation:

```bash
curl -fsS https://matrix.tom-mendy.com/.well-known/matrix/client | jq .
curl -fsS https://matrix.tom-mendy.com/.well-known/matrix/server | jq .
curl -fsS https://matrix.tom-mendy.com/_matrix/client/versions | jq .
curl -fsS https://rtc.tom-mendy.com/healthz
```

Also test `matrix.tom-mendy.com` with the public Matrix Federation Tester.

## First account and Authentik access

The first Matrix account becomes the Tuwunel administrator. Before creating the
bot, sign in at `https://chat.tom-mendy.com` with the homelab owner through
Authentik. Add other human users to `matrix-users`; `homelab-admins` are already
authorized by the Authentik blueprint.

Keep `login_with_password = false`. Do not expose `/_synapse/admin` through the
Ingress. Create the `hermes-bot` account only through a local port-forward and
the Synapse-compatible shared-secret registration endpoint:

```bash
kubectl port-forward -n matrix svc/tuwunel 8008:8008
```

In another terminal, create the bot and capture its token without displaying
either secret:

```bash
umask 077
kubectl get secret matrix-runtime -n matrix \
  -o jsonpath='{.data.registration-shared-secret}' \
  | base64 -d > /tmp/matrix-registration-secret
./scripts/register-hermes-matrix-bot.py \
  /tmp/matrix-registration-secret /tmp/hermes-matrix-token
```

Copy `/tmp/hermes-matrix-token` into Infisical as
`/matrix/HERMES_MATRIX_ACCESS_TOKEN`. Also create
`/matrix/HERMES_MATRIX_ALLOWED_USERS` with your own full Matrix ID, for example
`@tom:matrix.tom-mendy.com`; multiple IDs are comma-separated. Then securely
delete both temporary files. Never paste token values into Git or shell history.
The Coder template configures Hermes with:

- Homeserver: `https://matrix.tom-mendy.com`
- User ID: `@hermes-bot:matrix.tom-mendy.com`
- Access token: `/matrix/HERMES_MATRIX_ACCESS_TOKEN`
- Allowed users: `/matrix/HERMES_MATRIX_ALLOWED_USERS`
- Recovery key: `/matrix/HERMES_MATRIX_RECOVERY_KEY`

Restrict Hermes' allowed Matrix users or rooms before starting its gateway.

## Hermes E2EE recovery key

Bootstrap cross-signing once from the Hermes workspace without printing the
generated recovery key:

```bash
hermes gateway stop
MATRIX_RECOVERY_KEY_OUTPUT_FILE=/tmp/hermes-matrix-recovery-key \
  hermes gateway run
```

Copy the `0600` file into Infisical as
`/matrix/HERMES_MATRIX_RECOVERY_KEY`, wait for `hermes-matrix` to synchronize,
then update the Coder workspace. After confirming that the gateway verifies its
device, securely delete the temporary file. Never regenerate the key merely to
recover old room messages; create a new encrypted room session instead.

## Calls

Cinny is the lightweight web client but does not provide the supported
MatrixRTC call path in this deployment. Use Element Desktop or Element X for
calls. TURN is intentionally omitted initially; add coturn only if calls fail
from restrictive or symmetric-NAT networks.

## Backup and recovery

Tuwunel data and online backups use separate `nfs-k8s` PVCs. Configure Synology
snapshots for both provisioned directories (daily, seven daily and four weekly
copies). From the first user's Tuwunel admin room, run these before upgrades:

```text
!admin server backup-database
!admin server list-backups
!admin server verify-backup <id>
```

Native database backups do not include media, so the Synology snapshot remains
required.

For recovery, stop the Tuwunel Deployment, restore both NFS directories from a
consistent snapshot, and start it again. To use a native backup instead, follow
the matching Tuwunel release's `--restore-backup` procedure while Tuwunel is
stopped. Perform a restore drill before treating the backup as valid.

## Node-loss check

Both PVCs use shared NFS and the Deployment has no node affinity. Test one node
at a time after a verified backup:

```bash
kubectl drain node2 --ignore-daemonsets --delete-emptydir-data
kubectl get pod -n matrix -o wide -w
kubectl uncordon node2
kubectl drain node3 --ignore-daemonsets --delete-emptydir-data
kubectl get pod -n matrix -o wide -w
kubectl uncordon node3
```

Do not drain both workers together.
