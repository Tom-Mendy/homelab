# Move Newt Credentials to Infisical

## Problem

Newt connector credentials were committed in `kubernetes/newt/newt-creds.yaml`.
The Newt Helm values already consume an existing Kubernetes Secret named
`newt-creds`, so the migration must preserve that Secret name and these keys:

```text
PANGOLIN_ENDPOINT
NEWT_ID
NEWT_SECRET
```

## Reasoning path

The existing Newt Argo CD application has a Git source at `kubernetes/newt`.
Replacing the committed Secret with a local Helm chart lets Argo CD continue to
own the same path while the Infisical operator creates `newt-creds`.

The new chart uses the v1beta1 Infisical operator resources:

- `InfisicalConnection`
- `InfisicalAuth`
- `InfisicalStaticSecret`

Before live sync, store the rotated Newt values in Infisical project `homelab`,
env `prod`, path `/newt`:

```text
PANGOLIN_ENDPOINT=<pangolin-url>
NEWT_ID=<rotated-or-current-newt-id>
NEWT_SECRET=<rotated-newt-secret>
```

The Kubernetes Auth machine identity is:

```text
name: newt-k8s-auth
identityID: 78e81396-214b-4ae1-9b8e-438fc2c31dee
namespace: newt-system
service account: newt-infisical-sync
```

## Commands and results

Render the local chart:

```sh
helm template test kubernetes/newt
```

Expected resources:

```text
ServiceAccount newt-infisical-sync
Secret newt-infisical-identity
InfisicalConnection newt-infisical
InfisicalAuth newt-infisical
InfisicalStaticSecret newt-creds
```

Validate the rendered chart against live cluster CRDs without applying it:

```sh
helm template test kubernetes/newt > /tmp/newt-infisical-render.yaml
kubectl apply --dry-run=server -f /tmp/newt-infisical-render.yaml
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

The committed Newt credentials were removed from Git. The `kubernetes/newt`
source now renders Infisical sync resources that recreate the same
`newt-creds` Kubernetes Secret for the upstream Newt chart.
