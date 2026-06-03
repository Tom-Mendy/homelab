# Replace CI Tarball Tool Installs

## Problem

Forgejo CI failed in `homelab-validation.yml` while installing Helm from the
official tarball:

```text
Install helm
curl: (35) Recv failure: Connection reset by peer
```

This happened after the previous fix moved Helm away from `apt` and into a
direct `curl` download from `get.helm.sh`. That avoided the missing apt package
problem, but still left CI dependent on ad hoc binary downloads from the runner.

After replacing the tarball installs with Actions, the first follow-up run
failed because Forgejo resolved the Gitleaks action through
`https://data.forgejo.org`, where that action does not exist:

```text
unable to clone 'https://data.forgejo.org/gitleaks/gitleaks-action'
remote: Not found.
fatal: repository 'https://data.forgejo.org/gitleaks/gitleaks-action/' not found
```

## Reasoning Path

Inspect the active Forgejo workflow:

```sh
sed -n '1,120p' .forgejo/workflows/homelab-validation.yml
```

Observed direct downloads:

```text
curl -sSL https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz
curl -sSL https://github.com/yannh/kubeconform/releases/download/...
curl -sSL https://github.com/gitleaks/gitleaks/releases/download/...
```

The replacement plan used maintained Actions where possible:

- `azure/setup-helm@v5.0.0` for Helm.
- `docker://ghcr.io/gitleaks/gitleaks:v8.30.1` for secret scanning.
- `docker://ghcr.io/yannh/kubeconform:master` for kubeconform.

The kubeconform Docker action validates files in the workspace. It does not
install a local `kubeconform` binary for shell scripts, so the workflow now
renders charts into `.forgejo-rendered/` before the Docker action validates that
directory.

## Command Results

Workflow changes:

```yaml
- name: Install helm
  uses: azure/setup-helm@v5.0.0
  with:
      version: v3.18.3
```

```yaml
- name: Scan for committed secrets
  uses: docker://ghcr.io/gitleaks/gitleaks:v8.30.1
  with:
      args: detect --source . --redact --no-banner --verbose
```

```yaml
- name: Validate rendered local charts with kubeconform
  uses: docker://ghcr.io/yannh/kubeconform:master
  with:
      entrypoint: /kubeconform
      args: >-
          -strict
          -summary
          -ignore-missing-schemas
          .forgejo-rendered
```

The checkout step now uses full history for secret scanning:

```yaml
- name: Checkout
  uses: actions/checkout@v6
  with:
      fetch-depth: 0
```

## Verification

Render all local charts:

```sh
./scripts/test-helm-chart.sh
```

Observed output:

```text
=== atuin ===
OK
...
=== vaultwarden ===
OK
```

Storage policy check:

```sh
./scripts/check-storage-policy.sh
```

Observed output:

```text
storage policy ok
```

Markdown check:

```sh
rumdl check --fix docs/activity_report/2026-06-03-replace-ci-tarball-tool-installs.md
```

Observed output:

```text
Success: No issues found in 1 file
```

Local kubeconform caveat:

```sh
./scripts/kubeconform-local-charts.sh
```

This can still fail locally if `kubeconform` is not installed. The Forgejo
workflow no longer depends on that local script; it validates rendered manifests
with the kubeconform Docker action.

Observed local output:

```text
kubeconform is required but was not found in PATH
```

Local gitleaks verification:

```sh
gitleaks detect --source . --redact --no-banner --verbose
```

Observed output:

```text
164 commits scanned.
scan completed in 279ms
no leaks found
```

## Final Outcome

Forgejo CI no longer downloads Helm, kubeconform, or gitleaks with ad hoc
tarball `curl` steps.

The validation flow now uses maintained Actions and Docker actions for tooling,
while keeping the existing Helm render/lint and storage policy checks.
