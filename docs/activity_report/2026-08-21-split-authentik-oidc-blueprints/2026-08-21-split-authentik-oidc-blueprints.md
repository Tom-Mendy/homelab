# Split Authentik OIDC blueprints

## Problem

`kubernetes/authentik/blueprints/oidc-clients.yaml` contained all groups,
proxy applications, and OIDC clients in one 619-line file. That made changes
to one client harder to review and maintain.

## Reasoning

The Helm template previously copied one file into one ConfigMap key:

```sh
sed -n '1,180p' kubernetes/authentik/templates/oidc-blueprint.yaml
```

The blueprint inventory showed 53 entries covering shared groups, four proxy
applications, and seven OIDC clients:

```sh
rg -n '^  - model:|^    id:' \
  kubernetes/authentik/blueprints/oidc-clients.yaml
```

The entries were split into numbered files by responsibility:

- `00-groups.yaml` contains shared groups.
- `10-proxy-applications.yaml` contains Hindsight, Radarr, Sonarr,
  qBittorrent, and the embedded outpost.
- `20-openwebui.yaml` through `70-matrix.yaml` contain one OIDC
  client each.

Each file remains a complete Authentik Blueprint with its own metadata. The
Intra-file provider and application references still use `!KeyOf`, where
entry order is explicit. Bindings to shared groups use `!Find` by group name,
because Authentik does not guarantee evaluation order across blueprint files.
The ConfigMap template now uses Helm's file glob to include every YAML file:

```yaml
{{- range $path, $_ := .Files.Glob "blueprints/*.yaml" }}
  {{ base $path }}: |
{{ $.Files.Get $path | nindent 4 }}
{{- end }}
```

No Kubernetes workload or storage configuration was changed.

## Commands and results

The Authentik chart rendered and linted successfully:

```text
helm lint kubernetes/authentik
1 chart(s) linted, 0 chart(s) failed

helm template test kubernetes/authentik
8 blueprint ConfigMap keys rendered
53 entries found before the split
53 entries found after the split

The original and split inventories also produced no diff for either entry IDs
or model types.
```

The complete local Helm chart test passed:

```text
./scripts/test-helm-chart.sh
24 local charts: OK
```

The required storage-policy check passed:

```text
./scripts/check-storage-policy.sh
storage policy ok
```

The repository-wide Markdown check was attempted as required, but it found
pre-existing issues unrelated to this change:

```text
rumdl check --fix .
Issues: Found 136 issues in 17/134 files
```

The new report was then checked independently:

```text
rumdl check --fix \
  docs/activity_report/2026-08-21-split-authentik-oidc-blueprints
0 issues
```

Kubeconform could not run because it is not installed in the workspace:

```text
./scripts/kubeconform-local-charts.sh
kubeconform is required but was not found in PATH
```

## Final outcome

The monolithic blueprint was replaced by eight focused blueprint files. The
Helm chart now packages all of them into the existing ConfigMap, preserving
the ConfigMap name and all 53 Authentik entries. Shared-group lookups do not
depend on the order in which Authentik evaluates the files.
