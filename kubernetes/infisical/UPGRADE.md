# Infisical application, chart and operator — staged source only

Nothing under `maintenance/` is referenced by Flux. The server application and
server chart remain unchanged. The operator was independently upgraded to
0.11.16; all 12 existing static-secret resources successfully reconciled against
the unchanged server. Do NOT treat the prepared server patches as a single atomic
upgrade or enable them without the gates below.

## Evidence / blockers

Restricted artifacts: `/opt/data/maintenance-snapshots/resume-stateful/`.
`pg_dump -Fc` from `infisical-postgres-1` succeeded; the archive was really restored
with `pg_restore --exit-on-error --no-owner --no-acl` into PostgreSQL 17.11 on a
new `nfs-k8s` PVC, under a deny-all NetworkPolicy, with no Service or Ingress.
All 795 application tables restored; pre-migration `isSecret` is still present.
This proves logical database restoration, NOT target migration, secret decryption,
role/ACL reconstruction, SSO or operator authentication. Same-NAS artifacts are
not independent backups. No live secret values were exported or printed.

Missing gates: approved encrypted off-cluster escrow of `infisical-secrets`
(including encryption/authentication keys and every effective configuration
secret), database role/privilege recovery, an explicit Redis queue persistence
and producer-drain decision, fresh final database backup, and an isolated
v0.167.4 migration/decryption/authentication rehearsal. Do not run a restored
Infisical with outbound integrations against production systems.

## Serialized GitOps procedure

1. Prepare immediate old-image resume (`replicaCount: 1`, chart 1.8.0) before
   maintenance. Hold the validated operator 0.11.16 unchanged during application migration.
2. Review Agent Vault clients and identity credential permissions. Stop/drain
   any external queue producers and make an explicit decision about preserving
   Redis state. Merge `01-quiesce.values.yaml` into active values, retaining OLD
   chart/image. Reconcile only Infisical; prove no old application Pods remain.
   Redis, PostgreSQL, credentials and all PVCs must remain preserved.
3. Produce/restore-test the final database backup plus independent encrypted key
   escrow. If any gate fails BEFORE migration, resume the old application
   promptly; do not leave production deliberately stopped.
4. While application replicas remain ZERO, merge `02-stage.values.yaml` into
   active values and merge `02-chart.helmrelease-patch.yaml` into ONLY the
   `infisical` HelmRelease in `kubernetes/flux/cluster/apps/identity.yaml`.
   Preserve all unrelated releases, CRD options and existing post-renderers.
   Render chart 1.12.0 and review the complete diff before reconciliation.
5. The chart does NOT expose a strategy value. The supplied Flux post-renderer
   sets RollingUpdate maxSurge=0/maxUnavailable=1 without changing strategy type.
   The separate zero-replica stage is still mandatory: no old Pod may remain
   when a new Pod starts migrations. Validate using the actual Helm applying
   manager; do not force replace a release or touch a PVC to resolve a conflict.
6. Only after the rehearsal/escrow gates, merge `03-resume.values.yaml` and
   reconcile Infisical alone. Verify migration logs, `/api/status`, SSO, existing
   identity authentication, decryption/read of a representative existing secret,
   and consumer sync without printing values. Check queues and Redis separately.
7. The independent operator operation is complete;
   `04-operator.helmrelease-patch.yaml` is retained as a reference, not a pending
   server migration stage. Preserve defaults disabling automatic default
   auth/connection creation and keep `defaultResourcesHelmHooks: false`.
   Verify installed CRDs,
   resource Ready conditions, auth and observed secret resourceVersions; do not
   delete/re-adopt existing live Secrets as an upgrade workaround.
8. After migration, rollback requires stopping all application Pods and restoring
   into a NEW PostgreSQL database/cluster on NFS plus the matching escrowed keys
   and reviewed connection configuration. Preserve originals; do not downgrade
   the app against the migrated database. Reconcile the old chart/image only
   once restore-based recovery has passed. Include post-backup write loss in
   the recovery decision.

## Packaging and upstream review

- Application target deliberately stays **v0.167.4**, although the checker now
  reports v0.167.5. Verified target digest is in `02-stage.values.yaml`.
- Chart 1.12.0 exists and bundles unchanged Redis 18.14.1/PostgreSQL 14.1.10
  dependency versions. External PostgreSQL remains disabled in the subchart;
  Redis PVC identity/storage must be preserved. Auto-bootstrap remains disabled.
- Chart 1.10 adds UID 1001 hardening; rehearse startup with that context.
  Chart 1.11 bootstrap namespace migration is inactive here because bootstrap
  is disabled. Chart 1.12 permits deterministic rendering with
  `rolloutOnEveryRender: false`; credential updates then need an explicit,
  separately authorized restart rather than timestamp-driven redeploys.
- 0.166.6 drops `agent_vault_variables.isSecret`; older Pods are incompatible.
  0.167.0 adds HSM metadata and removes bundled go-sidecar. No go-sidecar is
  configured in this deployment. Existing cloud identity authentication must
  still be tested separately from tightened create/update permissions.
- Operator tags use `infisical-k8-operator/v0.11.x` (not bare `v0.11.x`). Official
  comparison covers 171 commits: TLS/static-secret corrections, CRD/status/RBAC
  changes, opt-in adoption, default connection/auth resources, concurrency and
  Helm hooks. Default new auth/connection resources remain disabled. Chart
  0.11.16 resolves and its default operator image is v0.11.16. No separate bare
  semantic-version GitHub release entries were found.

Sources:

- <https://github.com/Infisical/infisical/tree/v0.167.4/upgrade-impact/data/releases>
- <https://github.com/Infisical/infisical/blob/v0.167.4/backend/src/db/migrations/20261009145434_drop-agent-vault-variable-is-secret.ts>
- <https://github.com/Infisical/kubernetes-operator/compare/infisical-k8-operator/v0.11.0...infisical-k8-operator/v0.11.16>
- <https://dl.cloudsmith.io/public/infisical/helm-charts/helm/charts/>
