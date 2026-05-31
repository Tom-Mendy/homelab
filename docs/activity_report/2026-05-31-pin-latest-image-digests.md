# Pin Latest Image Digests

## Problem

Several workloads used `latest` image tags. A restart could pull different image
content without any Git change, which breaks reproducibility.

## Reasoning

The first safe fix was to pin each workload to the digest already running in the
cluster. This keeps the runtime image bytes unchanged and makes future upgrades
explicit.

Command used:

```sh
kubectl get pods -A -o json \
  | jq -r '
      .items[] as $p
      | $p.status.containerStatuses[]?
      | select(.image | test(":latest$|act-latest$"))
      | [$p.metadata.namespace, $p.metadata.name, .name, .image, .imageID]
      | @tsv
    '
```

The command returned the running image digests for Atuin, Blocky, Homepage,
media apps, Navidrome, Newt, Ollama, SearXNG, Stirling PDF, and Vaultwarden.

## Changes

Pinned these workloads to `latest@sha256:...` digests:

- Atuin
- Blocky
- Homepage
- Media apps and Gluetun sidecars
- Navidrome
- Newt
- Ollama
- SearXNG and Gluetun sidecar
- Stirling PDF
- Vaultwarden

## Outcome

These workloads no longer float to newer image content on restart. Future image
upgrades now require an explicit Git diff.

Remaining `latest` values:

- Endfield still uses `latest`; no completed CronJob pod existed to read the
  running digest because the job TTL had already cleaned it up. It should be
  pinned after CI publishes immutable tags or the registry digest is known.
- GitHub ARC runner scale sets still use `ghcr.io/actions/actions-runner:latest`;
  no runner pod was active during this pass to read a digest.
- Wakapi still uses `latest`, but no Argo CD application currently points at the
  Wakapi chart.

Validation:

```text
storage policy ok
Success: No issues found in 3 files
git diff --check
./kubernetes/test-helm-chart.sh
OK for all tested charts
kubectl apply --dry-run=server -f /tmp/homelab-pin-render.yaml
all rendered resources accepted by the API server
```
