# Add the Traefik 4475 dashboard to Grafana

## Problem

The repository contained `kubernetes/grafana/dashboards/traefik.json`, but the
Grafana dashboard ConfigMap did not provision it. That file also expected both
Prometheus and Loki, while this Grafana deployment only configures Prometheus.

Dashboard 4475 revision 5 was requested as the replacement. Before provisioning
it, its datasource import placeholder and variables had to be adapted for the
existing file-based Grafana provisioning.

## Reasoning and investigation

The requested revision was inspected directly:

```console
$ curl -fsSL \
  https://grafana.com/api/dashboards/4475/revisions/5/download |
  jq '{uid,title,schemaVersion,panels:(.panels|length)}'
{
  "uid": "qPdAviJmz",
  "title": "Traefik",
  "schemaVersion": 27,
  "panels": 9
}
```

It contains seven Prometheus expressions using these metric families:

```text
traefik_service_requests_total
traefik_service_request_duration_seconds_sum
traefik_entrypoint_requests_total
```

The live Prometheus server already contained all three:

```text
traefik_service_requests_total                    54
traefik_service_request_duration_seconds_sum      54
traefik_entrypoint_requests_total                 24
```

The Traefik metrics target was healthy:

```text
kubernetes-pods  10.233.71.4:9100  http://10.233.71.4:9100/metrics  up
```

No Prometheus or Traefik configuration change was therefore required.

The dashboard uses the historical `graph` and `singlestat` panel types.
Grafana 12 removed Angular support and force-migrates old core panels to their
React replacements. Grafana 13 also migrates existing dashboards to its current
schema when they are opened. Using that native migration avoids adding a plugin
or maintaining a hand-written conversion of old panel options.

## Changes

`kubernetes/grafana/dashboards/traefik.json` was replaced with dashboard 4475
revision 5 and adapted:

- official title `Traefik` and UID `qPdAviJmz`;
- one-hour initial range and one-minute refresh;
- attribution link to the original dashboard;
- removal of the import-only `__inputs`;
- one dynamic `${DS_PROMETHEUS}` datasource variable;
- Prometheus datasource objects on every query panel and target;
- service values restricted to `traefik_service_requests_total`;
- entrypoint values restricted to `traefik_entrypoint_requests_total`;
- `All` selected by default for entrypoints.

The existing ConfigMap template now provisions `traefik.json`:

```yaml
traefik.json: {{ .Files.Get "dashboards/traefik.json" | b64enc | quote }}
```

No Loki datasource, plugin, ServiceMonitor, scrape job, PVC, or StorageClass was
added.

## Validation results

The JSON metadata and structure were checked:

```text
title: Traefik
uid: qPdAviJmz
panels: 9
PromQL targets: 7
Loki/import placeholders: none
Non-dynamic Prometheus datasource UIDs: 0
```

All seven expressions were evaluated against the live Prometheus server using
the existing service
`authentik-authentik-server-80@kubernetes` and `entrypoint=.*`:

```text
PromQL targets checked: 7
PromQL failures: 0
service return code: 1 result
service response time: 1 result
service request rate: 1 result
HTTP 200 rate: 5 results
other HTTP status rate: 19 results
requests by service: 15 results
requests by entrypoint: 2 results
```

The chart and storage checks passed:

```console
$ jq empty kubernetes/grafana/dashboards/traefik.json
$ helm lint kubernetes/grafana
1 chart(s) linted, 0 chart(s) failed

$ helm template grafana-local-extras kubernetes/grafana --namespace grafana
ConfigMap binaryData keys:
argocd.json, blocky.json, kubernetes.json, node-exporter.json, traefik.json

$ ./scripts/check-storage-policy.sh
storage policy ok
```

The five provisioned dashboards total 900432 bytes, leaving 148144 bytes below
the 1 MiB ConfigMap limit. No active Kubernetes manifest uses `local-path`.

The required repository-wide Markdown fixer reported pre-existing issues and
reformatted two unrelated files:

```console
$ rumdl check --fix .
Fixed: Fixed 167/229 issues in 2 files
```

Those unrelated edits were reverted. The new report passed its focused check:

```console
$ rumdl check \
  docs/activity_report/2026-07-23-add-traefik-grafana-dashboard/\
2026-07-23-add-traefik-grafana-dashboard.md
Success: No issues found in 1 file
```

## Final outcome

The repository now provisions the requested Traefik 4475 dashboard through the
existing GitOps-managed Grafana ConfigMap. The live cluster was only queried for
validation; no resource was applied directly, and no commit or push was made.

After the change reaches the GitOps branch, the remaining checks are to confirm
Grafana provisioning in its logs and open the dashboard with `All`, `web`, and
`websecure` entrypoint selections.
