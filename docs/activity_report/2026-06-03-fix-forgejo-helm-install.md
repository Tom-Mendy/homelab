# Fix Forgejo Helm Install

## Problem

Forgejo `homelab-validation` failed during `Install system tools`:

```text
W: Failed to fetch https://packages.microsoft.com/ubuntu/24.04/prod/...
Could not wait for server fd - select (11: Resource temporarily unavailable)
W: Some index files failed to download.
E: Unable to locate package helm
```

The workflow installed Helm through `apt-get install -y curl helm ripgrep`.
On the Forgejo Ubuntu runner, the Helm package was not available after a flaky
external apt index update.

## Reasoning Path

Inspect the active Forgejo validation workflow:

```sh
sed -n '1,240p' .forgejo/workflows/homelab-validation.yml
```

Observed install step:

```yaml
- name: Install system tools
  run: |
      apt-get update
      apt-get install -y curl helm ripgrep
```

Search for other Helm install patterns:

```sh
rg -n "helm|Install system tools|validation|apt|check-storage-policy" \
  .forgejo workflows scripts kubernetes docs -S
```

The command also reported `rg: workflows: No such file or directory`, because
there is no top-level `workflows/` path. Useful matches showed this workflow was
the active Forgejo validation entrypoint.

The fix was to stop depending on Ubuntu apt repositories for Helm. The workflow
now installs only `curl` and `ripgrep` from apt, then installs a pinned Helm
release from the official Helm tarball.

## Command Results

Storage policy check:

```sh
./scripts/check-storage-policy.sh
```

```text
storage policy ok
```

Confirm no active Kubernetes manifest uses `local-path`:

```sh
rg -n "local-path" kubernetes .forgejo docs --glob '!docs/activity_report/**'
```

```text
docs/kubernetes-storage.md:18:Do not use `local-path` ...
docs/kubernetes-storage.md:20:Some legacy PVCs still use `local-path` ...
docs/kubernetes-storage.md:21:manifests are listed in ...
docs/kubernetes-storage.md:30:## Migrating an existing local-path PVC
docs/kubernetes-storage.md:51:5. Delete the old `local-path` PVC ...
docs/kubernetes-storage.md:59:8. Remove any old local-path PV ...
```

Helm chart lint and render check:

```sh
./scripts/test-helm-chart.sh
```

```text
=== atuin ===
OK
...
=== vaultwarden ===
OK
```

Secret scan:

```sh
gitleaks detect --source . --redact --no-banner --verbose
```

```text
159 commits scanned.
scan completed in 253ms
no leaks found
```

Local kubeconform availability check:

```sh
./scripts/kubeconform-local-charts.sh
```

```text
kubeconform is required but was not found in PATH
```

No local `kubeconform` binary was found. This local failure confirms the script
guard works. The Forgejo workflow installs `kubeconform` before running it.

## Final Outcome

`.forgejo/workflows/homelab-validation.yml` now defines `HELM_VERSION`, removes
`helm` from apt install, and adds a dedicated Helm install step:

```yaml
- name: Install helm
  run: |
      curl -sSL \
        "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" \
        -o /tmp/helm.tar.gz
      tar -C /tmp -xzf /tmp/helm.tar.gz linux-amd64/helm
      install /tmp/linux-amd64/helm /usr/local/bin/helm
      helm version
```

The validation job no longer depends on `apt` locating a `helm` package.
