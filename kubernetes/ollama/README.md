# Ollama quick commands

## Pull a model

Avoid hard-coded pod names by selecting the first pod dynamically:

```bash
POD=$(kubectl get pod -n ollama -l app=ollama -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n ollama "$POD" -- ollama pull MODEL_NAME:TAG
```

Example:

```bash
POD=$(kubectl get pod -n ollama -l app=ollama -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n ollama "$POD" -- ollama pull gemma3:4b
```

## List installed models

```bash
POD=$(kubectl get pod -n ollama -l app=ollama -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n ollama "$POD" -- ollama list
```

For the former Ubuntu installation, node `node3` used the NVIDIA 580 driver
branch or newer and
`nvidia-container-toolkit` 1.20.1 or newer for the pinned Ollama release. These
host packages are not reconciled by Flux because this repository has no node
configuration controller. After rebuilding the node, install those packages,
reboot it, and verify that Kubernetes advertises `nvidia.com/gpu: 1` before
allowing Ollama to schedule there.

For the Talos installation, the pinned Ollama 0.40.13 image was validated
on node3's GTX 1080 with the Talos v1.14.5 NVIDIA extension, driver
580.178.04, and toolkit 1.19.1. The validation generated text and
`ollama ps` reported 100% GPU. Verify GPU allocation and inference again
after changing the pinned runtime or image.
