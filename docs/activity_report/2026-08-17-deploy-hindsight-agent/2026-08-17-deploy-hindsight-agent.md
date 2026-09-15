# Deploy Hindsight as an internal agent service

## Problem

Hermes attempted to install `hindsight-all` into the read-only Python
environment supplied by its official container image. A temporary writable
copy worked but consumed 5.8 GiB and mixed the lifecycle of the memory service
with the interactive Coder workspace.

## Reasoning and commands

The failed local installation exposed two separate issues. The image
environment is owned by root, and the unversioned Hindsight dependency had
advanced beyond the versions supported by Hermes 0.18.0:

```console
$ uv pip check --python /opt/data/.runtime-venv-v2026.7.1/bin/python3
Found 11 incompatibilities
```

The official Hindsight 0.6.1 release publishes a dedicated API-only image and
supports an embedded PostgreSQL database under `/home/hindsight/.pg0`. Its
documented health endpoint is `/health`, and its native Ollama provider accepts
an OpenAI-compatible base URL. The multi-architecture image was pinned before
deployment:

```console
$ docker buildx imagetools inspect \
    ghcr.io/vectorize-io/hindsight-api:0.6.1 \
    --format '{{json .Manifest}}'
"digest": "sha256:ba832685d530055ee32c23ee4a02100bf6dc9d932f28b1c4d03c6dd33fbacaef"
```

Hermes still invokes `uv --upgrade` for the already-baked client. Generating a
constraint file from the immutable environment makes that operation a no-op
without maintaining a second virtual environment:

```console
$ uv pip freeze --python /opt/hermes/.venv/bin/python3 \
    | grep -v '^-e ' > /tmp/hermes-freeze-constraints.txt
$ UV_CONSTRAINT=/tmp/hermes-freeze-constraints.txt uv pip install \
    --python /opt/hermes/.venv/bin/python3 --quiet --upgrade \
    'hindsight-client>=0.6.1'
client-check-ok
```

## Validation results

The new chart and the complete active chart set passed Helm validation. The
first global run found a stale `.coder/pprof` socket created by the Coder CLI,
which Helm refuses to package. Adding that runtime directory to `.helmignore`
fixed the recurring problem.

```console
$ helm lint kubernetes/hindsight
1 chart(s) linted, 0 chart(s) failed

$ ./scripts/test-helm-chart.sh
=== hindsight ===
OK
...
=== vaultwarden ===
OK
```

The initial direct `kubeconform` invocation failed because the executable was
not in `PATH`. Supplying it through Nix validated both the chart and complete
Flux rendering:

```console
$ nix shell nixpkgs#kubeconform -c kubeconform \
    -strict -ignore-missing-schemas -summary /tmp/hindsight-rendered.yaml
Summary: 3 resources found in 1 file - Valid: 3, Invalid: 0, Errors: 0, Skipped: 0

$ nix shell nixpkgs#kubeconform -c kubeconform \
    -strict -ignore-missing-schemas -summary /tmp/hindsight-flux-rendered.yaml
Summary: 69 resources found in 1 file - Valid: 18, Invalid: 0, Errors: 0, Skipped: 51

$ ./scripts/check-storage-policy.sh
storage policy ok

$ terraform validate
Success! The configuration is valid.
```

The 1.4 GB image took 4 minutes and 19 seconds to pull. The first container
initialized PostgreSQL, embeddings, and reranking correctly, but its Ollama
connection check contended with an existing generation. The default 120-second
LLM timeout expired, and the ten-minute startup probe restarted the pod. A
600-second LLM timeout and twenty-minute startup window allow the shared CPU
Ollama service to finish loading without weakening liveness checks.

The second rollout became ready and passed the request from Hermes:

```console
$ kubectl get deployment,pod,service,pvc -n agent
deployment.apps/hindsight   1/1
pod/hindsight-...           1/1   Running
service/hindsight           ClusterIP   8888/TCP
persistentvolumeclaim/hindsight-data   Bound   10Gi   nfs-k8s

$ curl -fsS http://hindsight.agent.svc.cluster.local:8888/health
{"status":"healthy","database":"connected"}
```

The final Hermes template uses `/opt/hermes/bin/hermes`, exports the external
service URL, and makes the wizard's client upgrade a no-op through frozen
constraints. The discarded local venv and uv cache were then removed from the
Hermes PVC:

```console
$ uv pip install --python /opt/hermes/.venv/bin/python3 --quiet --upgrade \
    'hindsight-client>=0.6.1'
$ uv cache clean
Removed 46321 files (5.7GiB)
```

## Final outcome

Hindsight runs as a private ClusterIP service in the `agent` namespace. Its
embedded database uses a dedicated `nfs-k8s` PVC, and its LLM requests use the
existing Ollama service and `gemma4:e4b`. Hermes keeps only the lightweight
client and connects over the cluster network. The Deployment has no node
affinity and its data is on Synology NFS, so it can be recreated on either
worker without stranding the database.
