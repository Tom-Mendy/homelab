# Remove Committed Grafana Admin Secret

## Problem

Grafana admin credentials were committed in
`kubernetes/grafana/grafana-admin-secret.yaml` and duplicated in the local
Grafana values. The upstream Grafana Helm chart can generate the admin secret
itself, so this repository does not need to manage `admin-user` or
`admin-password`.

## Reasoning path

The Grafana Helm documentation says the chart notes include how to decode the
admin password from the generated Kubernetes Secret, and shows retrieving
`admin-password` from the release Secret after install.

The existing `grafana-values.yaml` pointed Grafana at a repository-managed
Secret:

```yaml
admin:
  existingSecret: grafana-admin
  userKey: admin-user
  passwordKey: admin-password
```

Removing this override lets the upstream chart manage the admin Secret.

## Commands and results

Render the local Grafana extras chart:

```sh
helm template test kubernetes/grafana
```

Expected result: only local extras such as dashboard ConfigMaps render; no
repository-managed admin Secret is rendered.

Render all local charts:

```sh
kubernetes/test-helm-chart.sh
```

Check repository storage policy:

```sh
./scripts/check-storage-policy.sh
```

Expected result:

```text
storage policy ok
```

## Final outcome

The repository no longer commits or renders Grafana admin credentials. Grafana
will use the upstream chart-managed admin Secret after Argo CD syncs the
application.
