# Enable Blocky Filtering and Its Grafana Dashboard

## Problem

Blocky exported Prometheus metrics but did not configure any denylist, so it
was acting only as a DNS proxy. The repository also contained an old MySQL
query-log dashboard at `kubernetes/grafana/dashboards/blocky.json`, but the
Grafana dashboard ConfigMap did not provision that file and Grafana did not
have a MySQL datasource.

The current Blocky image was `v0.30.0`. Blocky's official Grafana dashboard
uses browser-side canvas buttons to call the Blocky API, and cross-origin
requests from Grafana require a Blocky version newer than `v0.31`.

## Reasoning

Prometheus already discovered Blocky through the pod scrape annotations, so
adding another scrape configuration was unnecessary. The existing Grafana
13 deployment was also new enough for the official canvas panel.

The smallest complete change was therefore to:

1. Upgrade Blocky to the pinned `v0.33.0` image.
2. Configure HaGeZi Multi PRO as the strict policy for every client.
3. Add an HTTPS ingress for the API already exposed by Blocky's service.
4. Replace the unused MySQL dashboard with the official Prometheus dashboard.
5. Resolve the existing Prometheus datasource through a Grafana dashboard
   variable.

The single `strict` group uses HaGeZi Multi PRO as a standalone list.
`clientGroupsBlock.default` applies it to every client, so client names, PTR
records, and per-device mappings are unnecessary.

No PVC or list-download cache was added. Blocky's downloaded lists remain
stateless, and Grafana continues to use its existing `nfs-k8s` volume.

## Investigation and Commands

The initial live state showed Blocky `v0.30.0`, Grafana 13, and working
Prometheus discovery:

```sh
kubectl -n grafana get deploy grafana \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl -n blocky get deploy blocky \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
curl -kfsS \
  'https://prometheus.home.tom-mendy.com/api/v1/query?query=blocky_build_info'
```

Observed results:

```text
docker.io/grafana/grafana:13.0.1-security-01
spx01/blocky:v0.30.0@sha256:d9f15eddffedded40797406349012cbd5966ef99c286b13321e7a76efddb9bdc
job="kubernetes-pods", version="v0.30.0"
```

The current Blocky configuration validated with `v0.33.0`, but the command
identified three deprecated keys:

```sh
docker run --rm \
  -v "$PWD/kubernetes/blocky/config.yml:/app/config.yml:ro" \
  spx01/blocky:v0.33.0 \
  validate --config /app/config.yml
```

Initial result:

```text
WARN config option "upstream" is deprecated, please use "upstreams.groups" instead
WARN config option "port" is deprecated, please use "ports.dns" instead
WARN config option "httpPort" is deprecated, please use "ports.http" instead
INFO Configuration is valid
```

The configuration was migrated to the new keys. Repeating the validation then
returned:

```text
INFO Validating configuration file: /app/config.yml
INFO Configuration is valid
```

The remote list source was checked before rendering:

```sh
curl -fsSL --range 0-1023 \
  https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/pro-onlydomains.txt |
  head -5
```

The download succeeded and returned the expected HaGeZi Multi PRO header.

## Render and Dry-Run Results

The first Blocky render failed because its strict values schema did not yet
permit the new ingress values:

```text
Error: values don't meet the specifications of the schema(s):
additional properties 'ingress' not allowed
```

Adding an explicit ingress object to `values.schema.json` fixed that failure.
Both charts then passed linting:

```sh
helm lint kubernetes/blocky
helm lint kubernetes/grafana
```

```text
1 chart(s) linted, 0 chart(s) failed
1 chart(s) linted, 0 chart(s) failed
```

The charts were rendered and checked against the Kubernetes API:

```sh
helm template blocky kubernetes/blocky > /tmp/blocky-render.yaml
helm template grafana-local-extras kubernetes/grafana \
  > /tmp/grafana-render.yaml
kubectl apply --server-side --dry-run=server -f /tmp/blocky-render.yaml
kubectl apply --server-side --dry-run=server -f /tmp/grafana-render.yaml
```

The API accepted the Namespace, ConfigMap, Service, Deployment, Ingress, and
Grafana dashboard ConfigMap. It printed non-fatal field ownership warnings
because Argo CD manages the existing resources.

A first client-side dry-run of the Grafana ConfigMap failed:

```text
The ConfigMap "grafana-dashboards" is invalid:
metadata.annotations: Too long: may not be more than 262144 bytes
```

This happened because client-side apply attempted to store the large dashboard
payload in the `last-applied-configuration` annotation. Server-side dry-run
succeeded. The manifest already has `argocd.argoproj.io/sync-options:
Replace=true`, so Argo CD will replace the ConfigMap without creating that
annotation.

The dashboard was also checked for provisioning placeholders:

```sh
jq -e '.uid == "blocky-dns"' \
  kubernetes/grafana/dashboards/blocky.json
rg -n '\$\{DS_PROMETHEUS\}|VAR_BLOCKY_URL|http://blocky:4000|DS_MYSQL' \
  kubernetes/grafana/dashboards/blocky.json
```

The UID check passed. All Prometheus panels resolve the existing datasource
through the `DS_PROMETHEUS` dashboard variable, and the hidden API variable
contains `https://blocky.home.tom-mendy.com`.

## Grafana Datasource Provisioning Recovery

The first deployment attempted to assign the existing Prometheus datasource a
new fixed UID:

```yaml
name: Prometheus
uid: prometheus
```

Grafana stores the datasource created by the previous configuration in its
persistent SQLite database with an automatically generated UID. Provisioning
could not change that identity in place, so the new Grafana pod exited during
startup:

```sh
kubectl -n grafana logs grafana-68b495599-ftlf5 --previous
```

```text
Failed to provision data sources
Datasource provisioning error: data source not found
invalid service state: Failed
```

The fixed UID was removed. The Blocky dashboard now follows the already-working
Node Exporter dashboard pattern: a datasource variable selects the existing
Prometheus datasource by type, and panels reference `${DS_PROMETHEUS}`. This
preserves the datasource stored in Grafana and avoids a database migration.

The recovery rollout created `grafana-7b45cf956d-vkgjv`, which became `1/1
Running`. During the same sync, Argo CD tried to remove the bound PVC's
server-assigned `spec.volumeName` and Kubernetes rejected the immutable-field
patch:

```text
PersistentVolumeClaim "grafana" is invalid: spec: Forbidden:
spec is immutable after creation
```

The application now ignores only `/spec/volumeName` for the `grafana` PVC and
uses `RespectIgnoreDifferences=true`. This preserves the bound `nfs-k8s` volume
and prevents future syncs from attempting to clear its server-assigned name.

## Universal Filtering

The strict policy does not depend on client discovery:

```yaml
clientGroupsBlock:
  default:
    - strict
```

Every DNS request reaching Blocky uses HaGeZi Multi PRO. Runtime acceptance
only requires an arbitrary client to query a domain present in that list and
receive a blocked response.

## Storage and Markdown Checks

The required storage policy check was run:

```sh
./scripts/check-storage-policy.sh
rg -n --glob '*.yaml' --glob '*.yml' \
  'storageClassName:\s*local-path|storageClass:\s*local-path' kubernetes
```

Result:

```text
storage policy ok
no active local-path storage references
```

Markdown was formatted and checked with:

```sh
rumdl check --fix .
```

The repository-wide command exited nonzero because older Markdown files still
contain pre-existing line-length and heading violations. It also auto-fixed
two unrelated files; those unrelated formatter changes were reverted. The new
report was then checked directly:

```sh
rumdl check \
  docs/activity_report/2026-07-23-enable-blocky-filtering-grafana/\
2026-07-23-enable-blocky-filtering-grafana.md
```

```text
Success: No issues found in 1 file
```

## Final Outcome

The repository now contains:

- Blocky `v0.33.0`, pinned by manifest-list digest.
- Modern, non-deprecated Blocky configuration keys.
- HaGeZi Multi PRO strict filtering for every client.
- No hostname lookup or per-device mappings.
- A TLS ingress for `blocky.home.tom-mendy.com`.
- The official Blocky Prometheus dashboard with HTTPS control buttons.
- Dynamic selection of the existing Prometheus datasource.
- Provisioning of `blocky.json` through the existing dashboard ConfigMap.

The live cluster was not mutated manually because Argo CD owns these resources
and watches the repository's `main` branch. Rollout, CORS, control-button, and
live arbitrary-client filtering verification must be completed after these
changes are committed, pushed, and synchronized by Argo CD.
