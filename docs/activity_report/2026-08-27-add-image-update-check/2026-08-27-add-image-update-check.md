# Add a read-only image update check

## Problem

The repository pins many container images to exact digests, but it did not have
a small local command that could find stale pins and print the next image
reference. Manual registry checks do not scale well and can miss a digest change
behind an unchanged tag.

## Reasoning and commands

The existing repository conventions were checked first:

```sh
sed -n '1,220p' AGENTS.md
rg --files scripts | sort
rg -n '(^|[[:space:]])image:|repository:|tag:|digest:' kubernetes
for tool in crane skopeo docker podman yq jq; do
  command -v "$tool" || true
done
```

The repository prefers Python for new scripts. `crane` was not installed in the
development environment, while Docker, Podman, `yq`, and `jq` were available.
The script therefore uses the existing `crane` workflow from the image-pinning
activity and reports a clear installation error when `crane` is absent.

The script scans literal image references in YAML files and combines adjacent
`repository`, `tag`, and `digest` values from Helm values files. It skips Helm
template expressions. For semantic-version tags it selects the newest matching
major version and suffix. For unversioned or non-semantic tags it checks the same
tag's current digest. It never edits a file.

## Changes made

Added:

```text
scripts/check-image-updates.py
```

The command supports:

- `--path` to select a scan directory;
- `--all` to print current images as well as outdated images;
- `--allow-major` to include newer major versions;
- `--json` for CI or scheduled-job output;
- `--crane` to select the registry client executable.

The exit statuses are suitable for automation:

- `0`: all checked images are current;
- `1`: at least one image needs an update;
- `2`: the scan failed.

Updated `docs/update-guidance.md` with usage, output semantics, and a daily
read-only automation recommendation. The script does not open pull requests or
apply Kubernetes changes. A future automation job must still create a reviewed
Git change before Flux deploys an image.

## Validation

```sh
chmod +x scripts/check-image-updates.py
python3 -m py_compile scripts/check-image-updates.py
python3 scripts/check-image-updates.py --help
python3 scripts/check-image-updates.py --path /does/not/exist
```

Results:

```text
Python compilation: passed
Help output: passed
Invalid path: returned exit status 2 with a clear error
```

The full repository checks were also run:

```sh
./scripts/test-helm-chart.sh
./scripts/render-local-charts-for-kubeconform.sh
./scripts/check-storage-policy.sh
rumdl check --fix docs/update-guidance.md \
  docs/activity_report/2026-08-27-add-image-update-check/2026-08-27-add-image-update-check.md
git diff --check
```

The image scan itself could not query registries in this environment because
`crane` is not installed. Install `crane` before scheduling the command.

## Outcome

The repository now has a read-only command that reports stale tags or digests
and prints the exact replacement reference. It can run daily from a scheduler,
while Git review and Flux remain the deployment gate.
