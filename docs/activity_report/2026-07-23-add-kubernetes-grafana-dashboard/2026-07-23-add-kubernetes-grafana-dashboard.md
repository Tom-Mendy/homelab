# Add a Kubernetes cluster dashboard to Grafana

## Problem

Grafana already had dashboards for individual Linux nodes and applications,
but it did not provide a complete Kubernetes view covering nodes, namespaces,
pods, containers, network traffic, and persistent volumes.

Grafana dashboard 15661 revision 2 was selected as the starting point. It
could not be provisioned unchanged:

- it expected a VictoriaMetrics datasource import placeholder;
- every query filtered on an `origin_prometheus` label that does not exist in
  this cluster;
- its cAdvisor queries expected a `node` label, while the current Prometheus
  target only exposed the node name as `instance`;
- one target required application-specific Cassandra JVM metrics;
- two network targets used Docker-era container names that containerd does not
  expose.

## Reasoning and investigation

The existing Grafana chart already provisions dashboard JSON files from the
`grafana-dashboards` ConfigMap. Reusing that path was smaller and safer than
adding another dashboard provider or another ConfigMap.

The cluster was inspected before adapting the queries:

```console
$ kubectl get nodes
NAME    STATUS   ROLES           AGE    VERSION
node1   Ready    control-plane   166d   v1.34.3
node2   Ready    <none>          166d   v1.34.3
node3   Ready    <none>          166d   v1.34.3

$ kubectl get pods -n prometheus
prometheus-kube-state-metrics-...       1/1   Running
prometheus-prometheus-node-exporter-... 1/1   Running
prometheus-server-...                   2/2   Running
```

Prometheus returned live series for all core metric families used by the
dashboard:

```text
kube_node_info                                      3
kube_pod_info                                      79
container_cpu_usage_seconds_total                 256
container_memory_working_set_bytes                256
container_network_receive_bytes_total             574
kubelet_volume_stats_used_bytes                    25
```

A cAdvisor sample showed why the original node filters were empty:

```json
{
  "instance": "node1",
  "job": "kubernetes-nodes-cadvisor",
  "namespace": "kube-system",
  "pod": "calico-kube-controllers-...",
  "container": "calico-kube-controllers"
}
```

Adding `node` once in the Prometheus scrape relabeling is simpler than
rewriting every cAdvisor expression in the dashboard.

The first attempt to inspect the upstream chart through a local Helm repository
alias failed because the alias was not configured:

```console
$ helm show values prometheus-community/prometheus --version 29.9.0
Error: repo prometheus-community not found
```

Reading the pinned chart archive directly succeeded:

```console
$ helm show values \
  https://github.com/prometheus-community/helm-charts/releases/download/prometheus-29.9.0/prometheus-29.9.0.tgz
```

This confirmed that `scrapeConfigs.kubernetes-nodes-cadvisor.relabel_configs`
can override the list while the rest of the default scrape configuration is
merged from the chart.

## Changes

The revision 2 JSON was downloaded from:

```text
https://grafana.com/api/dashboards/15661/revisions/2/download
```

It was saved as
`kubernetes/grafana/dashboards/kubernetes.json` and adapted as follows:

- title `Kubernetes Cluster` and UID `k8s-cluster`;
- one-minute refresh and a default 30-minute time range;
- dynamic `${DS_PROMETHEUS}` datasource;
- `All` defaults for node, namespace, container, and pod filters;
- removal of the absent `origin_prometheus` label;
- removal of the Cassandra JVM target and two legacy Docker network targets;
- attribution link to the original Grafana dashboard.

The dashboard was added to the existing Grafana ConfigMap. Prometheus now adds
the Kubernetes node name to cAdvisor targets:

```yaml
scrapeConfigs:
  kubernetes-nodes-cadvisor:
    relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
      - source_labels:
          - __meta_kubernetes_node_name
        target_label: node
      - source_labels:
          - __metrics_path__
        target_label: metrics_path
```

## Validation results

Both local charts linted successfully:

```console
$ helm lint kubernetes/grafana
1 chart(s) linted, 0 chart(s) failed

$ helm lint kubernetes/prometheus
1 chart(s) linted, 0 chart(s) failed
```

Grafana and the pinned upstream Prometheus chart rendered successfully:

```console
$ helm template grafana-local-extras kubernetes/grafana --namespace grafana
$ helm template prometheus \
  https://github.com/prometheus-community/helm-charts/releases/download/prometheus-29.9.0/prometheus-29.9.0.tgz \
  --namespace prometheus \
  -f kubernetes/prometheus/prometheus-values.yaml
```

An initial attempt to parse the embedded Prometheus YAML with the installed
`yq` failed because this implementation does not provide `from_yaml`:

```text
jq: error: from_yaml/0 is not defined
```

Extracting the embedded configuration first allowed the rendered scrape job to
be checked. It contained exactly one `target_label: node` rule and retained
the `metrics_path` rule.

The dashboard and storage checks produced:

```text
Provisioned dashboard bytes: 881416 total
ConfigMap binaryData keys:
argocd.json, blocky.json, kubernetes.json, node-exporter.json
Forbidden dashboard placeholders: none
Non-dynamic Prometheus datasource UIDs: 0
PromQL targets checked: 100
PromQL API failures: 0
Queries returning current data before cAdvisor relabel rollout: 92
storage policy ok
active local-path manifests: none
```

The dashboard payload remains 167160 bytes below the 1 MiB ConfigMap limit.
The eight currently empty expressions filter cAdvisor by the new `node` label
and are expected to receive data after the GitOps synchronization reloads the
Prometheus configuration.

The required repository-wide Markdown fixer also reported pre-existing issues
and reformatted two unrelated files:

```console
$ rumdl check --fix .
Fixed: Fixed 167/229 issues in 2 files
```

Those unrelated automatic edits were reverted. The new report passes its
focused check:

```console
$ rumdl check \
  docs/activity_report/2026-07-23-add-kubernetes-grafana-dashboard/\
2026-07-23-add-kubernetes-grafana-dashboard.md
Success: No issues found in 1 file
```

## Final outcome

The repository now provisions a complete Kubernetes Grafana dashboard using
the existing Prometheus datasource and collectors. No dependency, PVC,
StorageClass, direct cluster apply, commit, or push was added.

After the changes reach the GitOps branch, Argo CD will synchronize Grafana and
Prometheus. The post-rollout checks are to confirm that
`count(container_cpu_usage_seconds_total{node!=""})` returns series and that
the dashboard works with both `All` and individual node or namespace filters.
