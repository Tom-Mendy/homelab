# Review Remaining Raw Kubernetes Manifests

## Problem

The GitOps reproducibility TODO still had a raw-manifest cleanup item open after
Blocky, Navidrome, Trilium, Prometheus, and Ollama were handled. The remaining
files needed to be reviewed so duplicate live resources could be removed while
intentional bootstrap and support files stayed in the repository.

## Reasoning Path

List remaining top-level YAML files under `kubernetes/` that are not chart
templates, chart values, Argo CD app definitions, or chart metadata:

```sh
find kubernetes -maxdepth 2 -type f \( -name '*.yaml' -o -name '*.yml' \) \
  | sort \
  | rg -v '/templates/|/argocd/apps/|values\.ya?ml$|Chart\.yaml$|values\.schema\.json$'
```

Useful result before this cleanup:

```text
kubernetes/argocd/argocd-ingress.yaml
kubernetes/blocky/config.yml
kubernetes/github-runners/arc-github-auth-secret.yaml
kubernetes/homepage/services.yaml
kubernetes/keel/keel-ingress.yaml
kubernetes/metallb/metallb-config.yaml
kubernetes/openwebui/openwebui-ingress.yaml
kubernetes/traefik/traefik-cloudflare-secret.example.yaml
```

Check whether Keel already rendered its ingress from the local chart:

```sh
helm template keel kubernetes/keel
```

Relevant rendered object:

```text
# Source: keel-local-extras/templates/ingress.yaml
kind: Ingress
metadata:
  name: keel-ingress
  namespace: keel
```

That matched the old raw ingress file, so the raw file was duplicate GitOps
input and could be removed.

Review OpenWebUI. Its Argo CD app used an external Helm chart for the
application and a raw local ingress file:

```yaml
- repoURL: ssh://git@forgejo.forgejo.svc.cluster.local/Tom-Mendy/homelab.git
  targetRevision: main
  path: kubernetes/openwebui
  directory:
    recurse: true
    include: openwebui-ingress.yaml
```

To match the Prometheus local-extras pattern, the raw ingress was converted into
a small local Helm chart at `kubernetes/openwebui`.

Review the GitHub ARC fallback token Secret. The active path now uses
`kubernetes/github-runners-auth` with Infisical to create `arc-github-auth`.
The old placeholder Secret file was no longer needed and was removed. The README
fallback was changed to a live `kubectl create secret` command so no token file
needs to be copied or edited.

## Command Results

Keel rendered successfully and proved the ingress existed in the chart:

```text
# Source: keel-local-extras/templates/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: keel-ingress
  namespace: keel
```

The following intentional support files stayed:

- `kubernetes/argocd/argocd-ingress.yaml` is a bootstrap manifest used by the
  Ansible Argo CD role.
- `kubernetes/metallb/metallb-config.yaml` is a bootstrap MetalLB CR manifest
  used by the Ansible MetalLB role.
- `kubernetes/homepage/services.yaml` is application config loaded into the
  Homepage chart ConfigMap, not a standalone Kubernetes manifest.
- `kubernetes/blocky/config.yml` is Blocky application config.
- `kubernetes/traefik/traefik-cloudflare-secret.example.yaml` is a docs-only
  break-glass example with placeholder values.

## Final Outcome

Removed duplicate or obsolete raw inputs:

- `kubernetes/keel/keel-ingress.yaml`
- `kubernetes/openwebui/openwebui-ingress.yaml`
- `kubernetes/github-runners/arc-github-auth-secret.yaml`

Added a local Helm extras chart for OpenWebUI:

- `kubernetes/openwebui/Chart.yaml`
- `kubernetes/openwebui/values.yaml`
- `kubernetes/openwebui/values.schema.json`
- `kubernetes/openwebui/templates/ingress.yaml`

Updated Argo CD to render `kubernetes/openwebui` as a chart source, updated
chart test coverage, and marked the raw-manifest review item complete in
`todo.md`.
