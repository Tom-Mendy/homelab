# Fix Unhealthy Cluster Pods

## Problem

`kubectl get pods -A` showed several unhealthy workloads:

- `metallb-system/controller` was in `CrashLoopBackOff`.
- `ollama/ollama` was stuck in `Init:CrashLoopBackOff`.
- `media/qbittorrent`, `media/nzbget`, and `searxng/searxng` had crashing
  `gluetun` sidecars.
- Some GitHub Actions runner pods/listeners were briefly `Error` or
  `Terminating`.

## Reasoning and Commands

List non-running pods and recent events:

```sh
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded -o wide
kubectl get events -A --sort-by=.lastTimestamp | tail -80
```

The phase selector missed CrashLoopBackOff pods, so container statuses were
checked directly:

```sh
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{range .status.containerStatuses[*]}{.name}:{.state.waiting.reason}{.lastState.terminated.reason}:{.restartCount}{" "}{end}{range .status.initContainerStatuses[*]}init/{.name}:{.state.waiting.reason}{.lastState.terminated.reason}:{.restartCount}{" "}{end}{"\n"}{end}' \
  | rg 'CrashLoopBackOff|Error|Init|[1-9][0-9]{2,}'
```

MetalLB logs showed the controller could not start:

```sh
kubectl logs -n metallb-system deploy/controller --all-containers --tail=120
```

Result:

```text
unable to get own pod for owner references
failed to create k8s client
```

The live deployment image had drifted to `quay.io/metallb/controller:main`
while the last-applied config showed `quay.io/metallb/controller:v0.14.5`.

The VPN sidecar logs were the same class of failure:

```sh
kubectl logs -n media deploy/qbittorrent -c gluetun --previous --tail=160
kubectl logs -n searxng deploy/searxng -c gluetun --previous --tail=160
```

Result:

```text
Wireguard settings: private key is not valid
```

The generated Kubernetes Secrets were present, but their decoded
`WIREGUARD_PRIVATE_KEY` values did not pass Gluetun validation. This requires
fixing the real values in Infisical, not a manifest change.

Ollama initially failed before model pull because node3 had an NVIDIA runtime
mismatch:

```sh
kubectl describe pod -n ollama -l app=ollama
ANSIBLE_HOST_KEY_CHECKING=False ansible -i ansible/inventory.ini node3 -m shell -a 'hostname; nvidia-smi || true; uname -r; dkms status 2>/dev/null || true'
```

Result:

```text
Failed to initialize NVML: Driver/library version mismatch
NVML library version: 535.309
nvidia/535.309.01, 6.8.0-111-generic, x86_64: installed
nvidia/535.309.01, 6.8.0-124-generic, x86_64: installed
```

After rebooting node3, `nvidia-smi` worked and the node booted
`6.8.0-124-generic`:

```sh
ANSIBLE_HOST_KEY_CHECKING=False ansible -i ansible/inventory.ini node3 -b -m reboot -a 'msg="Reboot node3 to clear NVIDIA driver/library mismatch" reboot_timeout=300 pre_reboot_delay=0 post_reboot_delay=20'
ANSIBLE_HOST_KEY_CHECKING=False ansible -i ansible/inventory.ini node3 -m shell -a 'nvidia-smi --query-gpu=name,driver_version --format=csv,noheader; uname -r'
```

Result:

```text
NVIDIA GeForce GTX 1080, 535.309.01
6.8.0-124-generic
```

Ollama then reached the model pull and failed because the pinned image was too
old:

```sh
kubectl logs -n ollama deploy/ollama -c pull-models --tail=80
```

Result:

```text
The model you are attempting to pull requires a newer version of Ollama.
```

The current Docker Hub stable tag was checked:

```sh
curl -fsSL 'https://registry.hub.docker.com/v2/repositories/ollama/ollama/tags?page_size=20&ordering=last_updated' \
  | jq -r '.results[] | [.name,.last_updated,.digest] | @tsv' | head -20
```

Result included:

```text
0.30.11 2026-06-26T18:26:05.031091Z sha256:c484b703176aa19dfc0a54cbfb60ab8094b38faa04283fb77eba1d33319e5eca
```

## Changes

MetalLB was restored live to the stable controller image:

```sh
kubectl set image -n metallb-system deployment/controller controller=quay.io/metallb/controller:v0.14.5
kubectl rollout status -n metallb-system deployment/controller --timeout=180s
```

Result:

```text
deployment "controller" successfully rolled out
```

Node3 was rebooted to clear the NVIDIA driver/runtime mismatch.

Ollama was updated in Git from:

```yaml
tag: 0.9.6@sha256:f478761c18fea69b1624e095bce0f8aab06825d09ccabcd0f88828db0df185ce
```

to:

```yaml
tag: 0.30.11@sha256:c484b703176aa19dfc0a54cbfb60ab8094b38faa04283fb77eba1d33319e5eca
```

## Verification

Storage policy was checked:

```sh
./scripts/check-storage-policy.sh
rg -n "local-path" kubernetes || true
```

Result:

```text
storage policy ok
```

No active manifest under `kubernetes/` matched `local-path`.

Local Helm validation could not be run because `helm` was not installed in the
shell:

```text
zsh:1: command not found: helm
```

## Outcome

MetalLB recovered after pinning back to `v0.14.5`.

Node3 recovered its GPU runtime after reboot.

Ollama still needed the GitOps image update pushed and synced so Argo CD would
stop reverting the live patch.

The VPN-routed media and SearXNG pods still require valid
`WIREGUARD_PRIVATE_KEY` values in Infisical. The manifests and Infisical sync
objects are present; the current secret values are invalid for Gluetun.

GitHub Actions runner listener churn was transient during inspection; the
`github-runners-capstone2` Argo CD app reported `Synced` and `Healthy`.
