# Move Endfield Secrets to Infisical

## Problem

Endfield committed private registry credentials, game account credentials, and a
Discord webhook in `kubernetes/endfield/values.yaml`.

The workloads consume two Kubernetes Secrets:

```text
forgejo-registry-creds
endfield-env
```

Those names must stay stable.

## Reasoning path

The chart already supports disabling literal Secret rendering with
`registryAuth.createSecret=false` and `env.createSecret=false`. The migration
adds Infisical v1beta1 resources that create the same target Secrets from
project `homelab`, env `prod`, path `/endfield`.

The Kubernetes Auth machine identity is:

```text
name: endfield-k8s-auth
identityID: b8b289b4-f869-4547-94e1-ce89928ce5a9
namespace: endfield
service account: endfield-infisical-sync
```

Infisical path `/endfield` must contain:

```text
REGISTRY_USERNAME
REGISTRY_PASSWORD
ENDFIELD_CRED
ENDFIELD_SK_GAME_ROLE
ENDFIELD_PLATFORM
ENDFIELD_VNAME
ENDFIELD_ACCOUNT_NAME
ENABLE_DISCORD_NOTIFY
DISCORD_WEBHOOK_URL
DISCORD_USER_ID
```

## Commands and results

Render the chart:

```sh
helm template test kubernetes/endfield
```

Expected resources include:

```text
ServiceAccount endfield-infisical-sync
Secret endfield-infisical-identity
InfisicalConnection endfield-infisical
InfisicalAuth endfield-infisical
InfisicalStaticSecret endfield-secrets
```

Validate against live CRDs without applying:

```sh
helm template test kubernetes/endfield > /tmp/endfield-infisical-render.yaml
kubectl apply --dry-run=server -f /tmp/endfield-infisical-render.yaml
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

The committed Endfield credentials were removed from Git. Infisical now owns
both Kubernetes Secrets used by the Endfield image pull and scheduled job.
