# Add the Sumfeet GitHub Actions runner scale set

Date: 2026-07-21

## Problem

The private GitHub repository `MrAmarok/sumfeet` needs self-hosted GitHub
Actions runners in the homelab cluster. Its Infisical token is stored under
the key `sumfleet_github_token`, while Actions Runner Controller (ARC) expects
the Kubernetes Secret key to be named `github_token`.

The runner must use the existing ARC controller and Infisical authentication
without exposing the token or adding worker-local storage.

## Reasoning and changes

The cluster already runs one shared ARC controller and repository-scoped runner
scale sets in `arc-runners`. The smallest compatible change was therefore to:

1. Add a second target to the existing `InfisicalStaticSecret`.
2. Render only `sumfleet_github_token` into that target as `github_token`.
3. Add one repository-scoped `gha-runner-scale-set` release.
4. Let the existing recursive Argo CD root application discover the new
   application manifest.
5. Use `self-hosted` as the scale set name because chart 0.13.1 uses that name
   as the GitHub routing label and does not expose additional scale set labels.

The new interfaces are:

- Infisical input: `sumfleet_github_token`
- Kubernetes Secret: `arc-github-auth-sumfeet`
- Kubernetes Secret key: `github_token`
- Workflow label: `self-hosted`
- Argo CD application: `github-runners-sumfeet`

The scale set follows the existing configuration: zero idle runners, up to five
runners, Docker-in-Docker mode, the pinned runner image, and the shared
controller service account. Its runner limit was adjusted to 4 CPU and 4 GiB
while the change was being deployed. It creates no persistent volumes.

## Commands and results

### Helm executable diagnosis

The initial command did not complete:

```console
$ timeout 10s helm version --short
helm_version_rc=124
```

Inspection showed that `helm` resolved to the unrelated Helm file manager,
version 0.9.0, rather than Kubernetes Helm:

```console
$ readlink -f "$(command -v helm)"
/nix/store/5s8rm29rscjrklfii63bfcvmwpqlrwy4-helm-0.9.0/bin/helm
```

Kubernetes Helm was therefore run directly from a temporary Nix shell:

```console
$ nix shell nixpkgs#kubernetes-helm --command helm version --short
v3.20.2+gv3.20.2
```

### Local chart validation

```console
$ helm lint kubernetes/github-runners-auth
==> Linting kubernetes/github-runners-auth
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

The rendered target contained only the required mapping:

```yaml
- name: arc-github-auth-sumfeet
  namespace: arc-runners
  kind: Secret
  creationPolicy: Orphan
  secretType: Opaque
  template:
    engineVersion: v1
    data:
      github_token: "{{ .sumfleet_github_token.Value }}"
```

The JSON values schema also parsed successfully:

```console
$ jq empty kubernetes/github-runners-auth/values.schema.json
$ echo $?
0
```

### ARC scale set rendering

<!-- rumdl-disable MD013 -->

```console
$ helm template arc-runner-set-sumfeet \
    oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
    --version 0.13.1 \
    -f kubernetes/github-runners/runner-scale-set-sumfeet-values.yaml
Pulled: ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set:0.13.1
Digest: sha256:39f9b61ee7e2865d7b8dd0e4e28b7c1a065765fc2ce5bf90874dd8e8be8ee2b2
```

<!-- rumdl-enable MD013 -->

The rendered `AutoscalingRunnerSet` contained:

```yaml
githubConfigUrl: https://github.com/MrAmarok/sumfeet
githubConfigSecret: arc-github-auth-sumfeet
runnerScaleSetName: self-hosted
```

### Kubernetes server dry-runs

<!-- rumdl-disable MD013 -->

```console
$ kubectl apply --dry-run=server -f /tmp/sumfeet-auth-render.yaml
serviceaccount/github-runners-infisical-sync configured (server dry run)
secret/github-runners-infisical-identity configured (server dry run)
infisicalauth.secrets.infisical.com/github-runners-infisical configured (server dry run)
infisicalconnection.secrets.infisical.com/github-runners-infisical configured (server dry run)
infisicalstaticsecret.secrets.infisical.com/arc-github-auth configured (server dry run)

$ kubectl apply --dry-run=server \
    -f kubernetes/argocd/apps/github-runners-sumfeet.yaml
application.argoproj.io/github-runners-sumfeet created (server dry run)

$ kubectl apply --dry-run=server -f /tmp/sumfeet-runner-render.yaml
serviceaccount/self-hosted-gha-rs-no-permission created (server dry run)
role.rbac.authorization.k8s.io/self-hosted-gha-rs-manager created (server dry run)
rolebinding.rbac.authorization.k8s.io/self-hosted-gha-rs-manager created (server dry run)
autoscalingrunnerset.actions.github.com/self-hosted created (server dry run)
```

<!-- rumdl-enable MD013 -->

### Repository policy checks

```console
$ ./scripts/check-storage-policy.sh
storage policy ok

$ git diff --check
$ echo $?
0

$ rg -n '[g]hp_|[g]ithub_pat_' \
    kubernetes/github-runners kubernetes/github-runners-auth \
    README.md docs/argocd-gitops.md
# no matches
```

The first Markdown check reported six `MD013` findings in the verbatim command
transcripts. Narrow `rumdl-disable MD013` directives were added around those
transcripts; the second check passed.

### Current GitOps state

Before this repository change is committed and reconciled, the existing auth
application remains healthy and the new resources are expectedly absent:

<!-- rumdl-disable MD013 -->

```console
$ kubectl get application github-runners-auth -n argocd \
    -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status \
    --no-headers
github-runners-auth   Synced   Healthy

$ kubectl get application github-runners-sumfeet -n argocd
Error from server (NotFound): applications.argoproj.io "github-runners-sumfeet" not found

$ kubectl get secret arc-github-auth-sumfeet -n arc-runners
Error from server (NotFound): secrets "arc-github-auth-sumfeet" not found
```

<!-- rumdl-enable MD013 -->

These `NotFound` results are useful confirmation that no manual deployment
bypassed GitOps. After the change reaches the tracked `main` branch, the root
application will create and reconcile both resources.

### Live reconciliation and label correction

The first live reconciliation used the concurrently adjusted name
`arc-runner-set-sumfeet-Tom`. Kubernetes rejected the uppercase character:

<!-- rumdl-disable MD013 -->

```console
ServiceAccount "arc-runner-set-sumfeet-Tom-gha-rs-no-permission" is invalid:
metadata.name: Invalid value: "arc-runner-set-sumfeet-Tom-gha-rs-no-permission":
a lowercase RFC 1123 subdomain must consist of lower case alphanumeric characters, '-' or '.'
```

<!-- rumdl-enable MD013 -->

The name was first normalized to lowercase. The requested GitHub label was
then set through the supported ARC 0.13.1 mechanism: the scale set itself was
renamed `self-hosted`. Adding `runnerScaleSetLabels` was not used because that
value is ignored by chart 0.13.1 and the installed CRD does not contain the
corresponding spec field.

Two RBAC resources from the rejected name were left in termination with the
ARC cleanup finalizer. They were removed after verifying their exact names:

<!-- rumdl-disable MD013 -->

```console
$ kubectl delete role arc-runner-set-sumfeet-Tom-gha-rs-manager \
    -n arc-runners
role.rbac.authorization.k8s.io "arc-runner-set-sumfeet-Tom-gha-rs-manager" deleted

$ kubectl delete rolebinding arc-runner-set-sumfeet-Tom-gha-rs-manager \
    -n arc-runners
rolebinding.rbac.authorization.k8s.io "arc-runner-set-sumfeet-Tom-gha-rs-manager" deleted

$ kubectl patch role arc-runner-set-sumfeet-Tom-gha-rs-manager \
    -n arc-runners --type=merge -p '{"metadata":{"finalizers":[]}}'
role.rbac.authorization.k8s.io/arc-runner-set-sumfeet-Tom-gha-rs-manager patched

$ kubectl patch rolebinding arc-runner-set-sumfeet-Tom-gha-rs-manager \
    -n arc-runners --type=merge -p '{"metadata":{"finalizers":[]}}'
rolebinding.rbac.authorization.k8s.io/arc-runner-set-sumfeet-Tom-gha-rs-manager patched
```

<!-- rumdl-enable MD013 -->

The final Argo CD and ARC state is healthy:

<!-- rumdl-disable MD013 -->

```console
$ kubectl get application github-runners-sumfeet -n argocd
github-runners-sumfeet   Synced   Healthy   Succeeded

$ kubectl get autoscalingrunnerset self-hosted -n arc-runners
self-hosted   0   5   https://github.com/MrAmarok/sumfeet   arc-github-auth-sumfeet

$ kubectl get autoscalinglisteners -A
arc-systems   self-hosted-fc6cdddb-listener   self-hosted

$ kubectl get pods -n arc-runners
self-hosted-k7pxr-runner-csgxw   Running   true
self-hosted-k7pxr-runner-llzv6   Running   true

$ kubectl get secret arc-github-auth-sumfeet -n arc-runners \
    -o go-template='{{range $k,$v := .data}}{{$k}{{"\\n"}}{{end}}'
github_token

$ kubectl get infisicalstaticsecret arc-github-auth -n arc-runners
LastReconcileStatus=True   Reconciliation successful
```

<!-- rumdl-enable MD013 -->

## Final outcome

The dedicated Sumfeet runner scale set and Kubernetes auth Secret are deployed
and healthy. The Secret is populated from `sumfleet_github_token` and exposes
only `github_token`. Helm rendering, Kubernetes server validation, the storage
policy, schema parsing, and whitespace checks pass.

Workflows in `MrAmarok/sumfeet` can select the runners with:

```yaml
runs-on: self-hosted
```
