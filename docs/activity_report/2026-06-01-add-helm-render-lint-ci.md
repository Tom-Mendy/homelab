# Add Helm Render And Lint CI

## Problem

`todo.md` required full Helm render and lint coverage in CI. The repository had
`kubernetes/test-helm-chart.sh`, but it only rendered charts locally and did not
fail the command when a chart failed.

## Reasoning Path

First check whether a CI workflow already existed:

```sh
find .github -maxdepth 3 -type f -print
```

Result:

```text
find: '.github': No such file or directory
```

Then inspect the existing local chart test script:

```sh
sed -n '1,220p' kubernetes/test-helm-chart.sh
```

The script listed local charts and ran `helm template`, but it only printed
`FAIL` and continued. That was useful for local feedback, but not strong enough
for CI because a failed chart could still leave the job green.

## Command Results

The script was updated to:

- run `helm lint` for every local chart;
- run `helm template` for every local chart;
- collect failures across charts;
- exit non-zero if any chart fails;
- use `kubernetes/active-local-charts.txt` so active local chart coverage stays
  explicit and shared with schema validation.

A GitHub Actions workflow was added at
`.github/workflows/kubernetes-validation.yml`:

```yaml
name: Kubernetes Validation
```

The workflow runs on pushes to `main` and on pull requests. It checks out the
repository, installs Helm, runs `./kubernetes/test-helm-chart.sh`, and runs
`./scripts/check-storage-policy.sh`.

## Final Outcome

The CI coverage item now has a real workflow and a failing local test script.
The same command can be run locally before pushing:

```sh
./kubernetes/test-helm-chart.sh
./scripts/check-storage-policy.sh
```
