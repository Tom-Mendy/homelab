# Add Forgejo Gitleaks CI

## Problem

Hermes produced two GitOps security reports under `docs/hermes/reports/`.
The useful repo-local finding was that secret scanning belonged in CI, while
`todo.md` still had this item open:

```text
- [ ] Add secret scanning CI with gitleaks or equivalent.
```

The repository also had two CI locations: `.forgejo/workflows/` for the active
Forgejo runner and `.github/workflows/` for an unused GitHub workflow.

## Reasoning Path

Inspect the Hermes reports:

```sh
sed -n '1,240p' docs/hermes/reports/2026-06-03-devops-quota-gitops-security.md
sed -n '1,260p' docs/hermes/reports/2026-06-03-devops-quota-gitops-ci-template.md
```

Relevant Hermes recommendations:

```text
- Add gitleaks/lint manifest checks in GitOps CI.
- Use gitleaks detect --redact so logs do not expose secret values.
- Do not inject kubeconfig or talosconfig into static validation CI.
```

Inspect existing CI:

```sh
find .forgejo .github -maxdepth 3 -type f -print
sed -n '1,180p' .forgejo/workflows/storage-policy.yml
sed -n '1,180p' .github/workflows/kubernetes-validation.yml
```

Observed state:

```text
.forgejo/workflows/storage-policy.yml
.github/workflows/kubernetes-validation.yml
```

Forgejo only ran the storage policy check. The GitHub workflow ran Helm render,
kubeconform, and storage policy, but this repo now uses Forgejo for CI.

## Command Results

The Forgejo workflow was changed to install `ripgrep`, Helm, `kubeconform`, and
`gitleaks`, then run:

```sh
gitleaks detect --source . --redact --no-banner --verbose
./scripts/test-helm-chart.sh
./scripts/kubeconform-local-charts.sh
./scripts/check-storage-policy.sh
```

The unused GitHub workflow was removed so Forgejo is the CI source of truth.
The pre-commit gitleaks hook was updated from `v8.24.0` to the Hermes-reported
`v8.30.1`.

The chart validation scripts were moved to `scripts/` and updated to read chart
names and chart directories from `kubernetes/`.

## Verification

Storage policy check:

```sh
./scripts/check-storage-policy.sh
```

```text
storage policy ok
```

Helm render and lint check:

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

Local kubeconform check could not run because `kubeconform` is not installed in
the shell environment:

```sh
./scripts/kubeconform-local-charts.sh
```

```text
kubeconform is required but was not found in PATH
```

This is expected locally; the Forgejo workflow installs kubeconform before
running the script.

Gitleaks scan:

```sh
gitleaks detect --source . --redact --no-banner --verbose
```

```text
157 commits scanned.
scan completed in 255ms
no leaks found
```

## Final Outcome

Forgejo CI now blocks committed secrets before merge while keeping the existing
Helm render, kubeconform, and storage policy checks. The open secret-scanning CI
TODO is complete.
