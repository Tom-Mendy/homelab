# Harbor

Harbor is deployed from the official `harbor/harbor` Helm chart. The chart
stores image data and job logs on `nfs-k8s` PVCs, and bootstrap credentials are
synced from Infisical at `/harbor`.

Before reconciliation, create an Infisical Kubernetes identity for the Harbor
namespace, grant it read access to `/harbor`, and replace
`REPLACE_WITH_HARBOR_INFISICAL_IDENTITY_ID` in `values.yaml`. Add these secrets
to the path:

- `HARBOR_ADMIN_PASSWORD`
- `HARBOR_SECRET_KEY` (16 characters)
- `HARBOR_CORE_SECRET` (16 characters)
- `HARBOR_JOBSERVICE_SECRET` (16 characters)
- `HARBOR_REGISTRY_SECRET` (16 characters)
- `HARBOR_REGISTRY_PASSWORD`
- `HARBOR_REGISTRY_HTPASSWD` (bcrypt htpasswd entry for the registry user)

Harbor's OIDC provider is declared in the Authentik blueprint. After the first
deployment, configure OIDC in Harbor's Administration > Configuration page and
use the redirect URI displayed there.
