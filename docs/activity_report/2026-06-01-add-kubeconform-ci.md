# Add Kubeconform CI Validation

## Problem

`todo.md` required kubeconform or equivalent schema validation in CI. Helm
rendering catches template errors, but it does not validate rendered Kubernetes
objects against Kubernetes schemas.

## Reasoning Path

Check whether `kubeconform` was already installed locally:

```sh
command -v kubeconform || true
```

Result:

```text

```

The command was not present locally, so the CI workflow needed an install step.
The validation script also needed to fail clearly when `kubeconform` is missing.

The previous chart test script had a hard-coded list of chart names and missed
some active local charts. A shared chart list was added:

```text
kubernetes/active-local-charts.txt
```

This list covers active local charts rendered by Argo CD, including `atuin`,
`media`, `ollama`, and `stirling-pdf`. It intentionally excludes the unused
`wakapi` chart.

## Command Results

The new validation script renders each active local chart, then validates the
rendered YAML:

```sh
./kubernetes/kubeconform-local-charts.sh
```

The script runs:

```sh
kubeconform -strict -summary -ignore-missing-schemas <rendered-chart.yaml>
```

`-ignore-missing-schemas` is required because this repository renders custom
resources such as Infisical CRDs and RuntimeClass-related resources whose schemas
are not always available from kubeconform's default schema source.

CI now installs kubeconform from the pinned v0.6.7 release and runs:

```sh
./kubernetes/test-helm-chart.sh
./kubernetes/kubeconform-local-charts.sh
./scripts/check-storage-policy.sh
```

## Final Outcome

The GitOps reproducibility checks now include:

- Helm lint for every active local chart.
- Helm render for every active local chart.
- Kubeconform schema validation for rendered active local charts.
- Storage policy validation.

The TODO kubeconform CI item is complete.
