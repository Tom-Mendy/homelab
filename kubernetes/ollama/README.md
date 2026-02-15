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
