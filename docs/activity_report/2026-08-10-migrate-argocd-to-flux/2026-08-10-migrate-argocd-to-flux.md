# Migrate Argo CD manifests to Flux Operator

## Problem

The cluster applications were defined as 32 Argo CD Applications. The goal was
to replace Argo CD with Flux Operator and native Flux resources without moving
persistent data away from Synology NFS. Ansible had already been removed from
the repository, so the replacement also needed a small standalone bootstrap.

No live controller was changed during this repository activity. The live
cutover must follow `docs/flux-gitops.md` after these changes reach Forgejo.

## Reasoning and implementation

Flux Operator owns the Flux controller lifecycle through one `FluxInstance`.
Applications use native `HelmRelease`, `HelmRepository`, `OCIRepository`, and
`GitRepository` resources instead of Flux Operator ResourceSets.

Existing local charts and values files were reused. Kustomize generates hashed
ConfigMaps from the external-chart values files, and its name-reference
configuration updates each `HelmRelease.valuesFrom` reference automatically.
This avoids copying values into Flux manifests.

The generated bundle contains:

- 38 HelmReleases, including separate upstream and local-extra releases where
  Argo CD previously combined multiple sources.
- 10 HelmRepository sources.
- 2 OCIRepository sources for Actions Runner Controller.
- 15 generated values ConfigMaps.

Dependencies ensure NFS, CRD controllers, databases, Traefik, and Infisical are
ready before their consumers. Existing release names and Helm storage
namespaces are retained so Flux can adopt current Helm release records.

The OpenWebUI PVC changed from the Argo-specific `Prune=false` annotation to
`helm.sh/resource-policy: keep`. Argo configuration, its ingress, homepage/DNS
entry, and Grafana dashboard were removed. The Flux Operator web UI was later
enabled with its own TLS ingress and Authentik OIDC authentication.

## Commands and results

Build the Flux Kustomization:

```text
$ kubectl kustomize kubernetes/flux/cluster
error: ... security; file ... is not in or below .../cluster/apps
```

This first attempt failed because local kubectl enables Kustomize's root-only
load restriction. Flux uses `LoadRestrictionsNone`, so the equivalent local
check is:

```text
$ kubectl kustomize --load-restrictor=LoadRestrictionsNone \
    kubernetes/flux/cluster
helmreleases=38
helmrepositories=10
ocirepositories=2
configmaps=15
```

Dependency inspection found no duplicate release names, missing dependencies,
or cycles:

```text
$ yq ... releases.yaml | jq ...
{"count":38,"duplicates":[],"missingDependencies":[]}

$ yq ... releases.yaml | jq ... | tsort
38 /tmp/flux-release-order
```

The first external-chart render exposed two values-schema conflicts introduced
by the earlier values-file consolidation:

```text
Error: values don't meet the specifications ... newt:
additional properties 'secret', 'infisicalSecret', 'namespace' not allowed

Error: values don't meet the specifications ... traefik:
additional properties 'namespace', 'secret', 'infisicalSecret' not allowed
```

Those keys belong to the local-extra charts. The two upstream HelmReleases now
disable schema validation while template rendering remains tested. A strict
shell rerun rendered all pinned external charts successfully, including ARC
OCI charts at `0.14.2`.

Flux Operator bootstrap validation resolved the requested patch channel:

```text
$ helm template flux-operator \
    oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
    --version '0.58.x' ...
Pulled: ghcr.io/controlplaneio-fluxcd/charts/flux-operator:0.58.0
operator_deployments=1
operator_crds=4
```

The Nix package for the Flux Operator CLI was version `0.49.0` and failed while
building the current distribution artifact. The pinned `0.58.0` release binary
was then used instead:

```text
$ flux-operator build instance \
    -f kubernetes/flux/bootstrap/flux-instance.yaml
instance_objects=34
```

Local chart and storage checks:

```text
$ ./scripts/test-helm-chart.sh
23 charts: OK

$ nix shell nixpkgs#kubeconform --command \
    ./scripts/kubeconform-local-charts.sh
Invalid: 0, Errors: 0 for every chart

$ ./scripts/check-storage-policy.sh
storage policy ok

$ rg -n 'local-path' kubernetes --glob '*.yaml' --glob '*.yml'
no matches
```

The requested live-wins check compared SearXNG with its chart. The only
meaningful workload drift was its running image digest, so the repository was
updated to retain that digest. The remaining differences were Argo tracking
annotations and Kubernetes-generated metadata, which were not copied into Git.

Kubeconform also checked the rendered Flux Operator and Flux bundle:

```text
Summary: 75 resources found in 2 files - Valid: 21, Invalid: 0,
Errors: 0, Skipped: 54
```

The skipped objects are custom resources for which the generic kubeconform run
had no schema. The FluxInstance was separately built by the matching Flux
Operator CLI, and the native Flux resources were rendered by Kustomize.

The required repository-wide Markdown command fixed the new files but returned
existing line-length findings in historical reports and backlogs:

```text
$ rumdl check --fix .
Fixed: Fixed 179/306 issues in 6 files
```

Formatter changes outside this migration were restored. A targeted `rumdl
check` over all Markdown files changed by this activity then returned:

```text
Success: No issues found in 10 files
```

## Final outcome

The repository now has a validated Flux Operator bootstrap and native Flux
application definitions. All persistent workloads continue to use `nfs-k8s`
or approved static Synology NFS volumes. The live Argo-to-Flux ownership
transfer remains intentionally unexecuted until the migration is committed,
pushed to Forgejo, and performed through the documented maintenance-window
sequence.

## Flux Operator installation

Argo CD remains active while Flux is installed beside it. The OIDC client
secret had already been synchronized by Infisical, so the Operator was
installed without writing the secret to Git or shell history:

```text
helm upgrade --install flux-operator oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
  --version '0.58.x' --namespace flux-system \
  --values kubernetes/flux/bootstrap/values.yaml \
  --set-file web.config.authentication.oauth2.clientSecret=/dev/stdin --wait
Release "flux-operator" does not exist. Installing it now.
Pulled ... flux-operator:0.58.0
STATUS: deployed
```

The next required bootstrap input is the dedicated Forgejo deploy key and its
`known_hosts` file. Flux must not be switched on or Argo CD stopped until the
`flux-system` Secret can be created and the `FluxInstance` reports Ready.

## Argo CD removal

Flux had a Ready `FluxInstance`, GitRepository, Kustomization, and 38 Ready
HelmReleases before the cutover. The Argo application controller had already
been scaled to zero. The 33 Argo Applications were removed after clearing
their finalizers, which kept the workloads in place.

```text
kubectl -n argocd delete applications --all --wait=true
33 Applications deleted

helm uninstall argocd --namespace argocd --wait
release "argocd" uninstalled

kubectl delete namespace argocd --wait=true
namespace "argocd" deleted
```

Argo CD CRDs were retained by Helm's resource policy; they are inert without
the Argo controllers and can be removed separately after the migration has
been observed in production.
