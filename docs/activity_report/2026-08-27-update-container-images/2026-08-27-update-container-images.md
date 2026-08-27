# Update pinned container images

## Problem

The image update checker reported 24 outdated image references. Some had newer
compatible tags, while others used a tag without a digest. The repository uses
Flux to deploy the `main` branch, so the updates must remain pinned in Git and
must not be applied as temporary live-only changes.

## Reasoning and commands

The update candidates came from the read-only image check:

```sh
./scripts/check-image-updates.py --all
```

The registry output supplied for this activity included newer pins for BusyBox,
Forgejo, Forgejo Runner, Navidrome, Docker-in-Docker, the NymVPN sidecar,
GitHub Actions runners, Atuin, Homepage, Tuwunel, Wakapi, Hindsight, Infisical,
the NVIDIA device plugin, Ollama, PostgreSQL, Gluetun, SearXNG, Blocky,
Stirling PDF, and Vaultwarden.

Each replacement was copied as a complete `tag@sha256` reference. Images already
reported as current were left unchanged. The same new pin was used at every
location where an image appeared more than once.

The local environment did not contain `crane`, so the registry query could not
be repeated here:

```text
error: crane is required; install it or pass --crane /path/to/crane
```

The values and templates were checked for old references before validation:

```sh
rg -n \
  '1\.37\.0@sha256:9db7|actions-runner:2\.334\.0|navidrome:0\.61\.2' \
  kubernetes --glob '*.yaml' --glob '*.yml'
```

The search returned no old references.

## Changes made

Updated 24 image pins across 20 Kubernetes values or template files. The
changes include:

- application images and supporting services;
- test and init-container images;
- the Forgejo runner and Docker-in-Docker image;
- the NVIDIA device plugin used by Ollama;
- the private NymVPN sidecar digest.

No image reported as current was changed. No Kubernetes resource was applied
directly, and no Git commit or push was performed.

## Validation

```sh
./scripts/test-helm-chart.sh
./scripts/render-local-charts-for-kubeconform.sh
./scripts/check-storage-policy.sh
rumdl check --fix docs/update-guidance.md \
  docs/activity_report/2026-08-27-update-container-images/2026-08-27-update-container-images.md
git diff --check
```

Results:

```text
25 local Helm charts: passed
local chart rendering: passed
storage policy ok
Markdown: no issues found
git diff --check: no output
old image reference search: no matches
```

The next deployment check must happen after these changes are merged into
`main` and reconciled by Flux:

```sh
flux get helmreleases -A
kubectl get pods -A
kubectl rollout status deployment/<name> -n <namespace>
```

A read-only live check confirmed that the local changes have not reached the
cluster yet:

```text
Flux source: refs/heads/main@sha1:69fdbdeca20bc3a9205066f8c9311d4cb4d3e6d4
Selected HelmReleases: Ready
Selected application pods: Running
```

The running status describes the images already deployed from `main`; it does
not validate the new pins in the working tree. The new images will need a
second health check after the Git change is merged and reconciled.

## Outcome

The repository now contains the 24 exact image updates reported by the checker.
The change is ready for the normal Forgejo review and Flux deployment path.
Runtime health cannot be confirmed until the changes are merged into `main` and
Flux rolls out the new images.
