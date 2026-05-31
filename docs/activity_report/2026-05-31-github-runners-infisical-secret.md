# Move GitHub Runner Token to Infisical

## Problem

The GitHub Actions Runner Controller auth Secret contained a committed GitHub
token. The runner scale sets reference `arc-github-auth`, so the Kubernetes
Secret name must stay stable while the secret source moves out of Git.

## Reasoning path

The ARC runner scale-set values all reference:

```yaml
githubConfigSecret: arc-github-auth
```

The preferred migration is a small GitOps chart that creates the same
Kubernetes Secret from Infisical using the v1beta1 operator resources:

- `InfisicalConnection`
- `InfisicalAuth`
- `InfisicalStaticSecret`

The chart is disabled until a Kubernetes Auth machine identity exists for:

```text
namespace: arc-runners
service account: github-runners-infisical-sync
```

Before enabling the chart, store the rotated GitHub token in Infisical project
`homelab`, env `prod`, path `github-runners`:

```text
github_token=<rotated-github-token>
```

## Commands and results

Render the default chart. It is disabled by default and emits no resources until
the machine identity ID is available.

```sh
helm template test kubernetes/github-runners-auth
```

Result:

```text
```

Render the enabled path with a dummy identity ID:

```sh
helm template test kubernetes/github-runners-auth \
  --set infisicalSecret.enabled=true \
  --set infisicalSecret.identityID=dummy-identity
```

Expected resources:

```text
ServiceAccount github-runners-infisical-sync
Secret github-runners-infisical-identity
InfisicalConnection github-runners-infisical
InfisicalAuth github-runners-infisical
InfisicalStaticSecret arc-github-auth
```

Validate the repository storage policy:

```sh
./scripts/check-storage-policy.sh
```

Expected result:

```text
storage policy ok
```

Render all local charts covered by the repository helper:

```sh
kubernetes/test-helm-chart.sh
```

Relevant result:

```text
=== github-runners-auth ===
OK
```

Validate the rendered enabled chart against the live cluster CRD schemas without
applying it:

```sh
helm template test kubernetes/github-runners-auth \
  --set infisicalSecret.enabled=true \
  --set infisicalSecret.identityID=dummy-identity \
  > /tmp/github-runners-auth-render.yaml

kubectl apply --dry-run=server -f /tmp/github-runners-auth-render.yaml
```

Result:

```text
serviceaccount/github-runners-infisical-sync created (server dry run)
secret/github-runners-infisical-identity created (server dry run)
infisicalauth.secrets.infisical.com/github-runners-infisical
created (server dry run)
infisicalconnection.secrets.infisical.com/github-runners-infisical
created (server dry run)
infisicalstaticsecret.secrets.infisical.com/arc-github-auth
created (server dry run)
```

Scan for the removed token prefix:

```sh
rg -n '[g]hp_' kubernetes/github-runners kubernetes/github-runners-auth docs
```

Result:

```text
```

## Final outcome

The committed GitHub token was replaced with a placeholder. A new Argo CD
application, `github-runners-auth`, can create `arc-github-auth` from Infisical
before the runner scale sets sync. Live cutover still requires a rotated GitHub
token in Infisical and the real Kubernetes Auth machine identity ID in
`kubernetes/github-runners-auth/values.yaml`.
