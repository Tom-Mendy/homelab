# Move Keel Basic Auth Password to Infisical

## Problem

Keel committed its dashboard basic-auth password in
`kubernetes/keel/keel-values.yaml`.

The upstream Keel chart reads `BASIC_AUTH_PASSWORD` from the Kubernetes Secret
named `keel`, so the migration must preserve that Secret name and key.

## Reasoning path

The Keel chart supports external Secret management with:

```yaml
secret:
  create: false
  name: keel
```

The local chart now creates that Secret through Infisical v1beta1 resources.

The Kubernetes Auth machine identity is:

```text
name: keel-k8s-auth
identityID: 71f263fc-48c4-4359-aaea-bbe8c66d3054
namespace: keel
service account: keel-infisical-sync
```

Infisical project `homelab`, env `prod`, path `/keel` must contain:

```text
BASIC_AUTH_PASSWORD=<rotated-keel-password>
```

## Commands and results

Render the local Keel extras chart:

```sh
helm template test kubernetes/keel
```

Validate against live CRDs without applying:

```sh
helm template test kubernetes/keel > /tmp/keel-infisical-render.yaml
kubectl apply --dry-run=server -f /tmp/keel-infisical-render.yaml
```

Render the upstream Keel chart with repository values:

```sh
helm template keel keel \
  --repo https://charts.keel.sh \
  -f kubernetes/keel/keel-values.yaml \
  -n keel
```

Run repository checks:

```sh
kubernetes/test-helm-chart.sh
./scripts/check-storage-policy.sh
```

Expected storage result:

```text
storage policy ok
```

## Final outcome

The committed Keel basic-auth password was removed from Git. Infisical now owns
the `keel` Kubernetes Secret consumed by the upstream Keel chart.
