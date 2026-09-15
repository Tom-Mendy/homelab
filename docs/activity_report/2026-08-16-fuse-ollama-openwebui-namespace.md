# Fuse Ollama and Open WebUI in the `ollama` namespace

## Problem

Ollama and Open WebUI were managed by separate Flux Helm releases and lived in
separate namespaces. Open WebUI needed to join the `ollama` namespace and local
Helm chart without losing its NFS-backed SQLite database, uploads, or vector
data. Both public HTTPS addresses must remain available.

## Reasoning path

The Open WebUI PVC is bound to the retained NFS PV
`pvc-090fcf5b-66f0-457f-9279-f5167b075af5`. A PVC cannot move namespaces, but
the PV can be released and rebound to a new PVC without copying the data.

Open WebUI is now a pinned dependency of the local `kubernetes/ollama` chart.
Its Helm values explicitly set `namespaceOverride: ollama`; without that
setting, a local render uses the current Helm namespace (`infisical` here).

For a migration before Flux removes the legacy releases, suspend them and stop
Open WebUI before the one-time PV transfer:

```sh
kubectl -n flux-system patch helmrelease/openwebui --type=merge \
  -p '{"spec":{"suspend":true}}'
kubectl -n flux-system patch helmrelease/openwebui-extras --type=merge \
  -p '{"spec":{"suspend":true}}'
kubectl -n openwebui scale statefulset/open-webui --replicas=0
kubectl -n openwebui delete pvc open-webui
kubectl get pv pvc-090fcf5b-66f0-457f-9279-f5167b075af5
kubectl patch pv pvc-090fcf5b-66f0-457f-9279-f5167b075af5 \
  --type=merge -p '{"spec":{"claimRef":null}}'
```

The NFS provisioner uses `Retain`, so deleting the old PVC does not delete its
Synology-backed data. Flux can then create `ollama/open-webui` with the same PV
name. After a healthy rollout, remove the empty `openwebui` namespace.

## Command results

The initial dependency download could not resolve DNS in the sandbox:

```text
Get "https://helm.openwebui.com/index.yaml": dial tcp: lookup
helm.openwebui.com: Temporary failure in name resolution
```

After allowing the Helm download, it completed successfully:

```text
Saving 1 charts
Downloading open-webui from repo https://helm.openwebui.com/
```

The first render exposed the upstream chart namespace default:

```text
name: open-webui
namespace: infisical
```

After setting `openwebui.namespaceOverride: ollama`, `helm template` renders
the Open WebUI PVC, Service, StatefulSet, and Ingress in `ollama`. The
storage-policy check returned:

```text
storage policy ok
```

After Flux applied the unified chart, Open WebUI remained pending because the
old claim still held the retained PV:

```text
pod/open-webui-0   0/1   Pending
persistentvolumeclaim/open-webui   Pending
pvc-090fcf5b-66f0-457f-9279-f5167b075af5   Bound   openwebui/open-webui
```

The legacy Helm releases had already been removed, and the old namespace had
no workload. The transfer was therefore safe to complete:

```sh
kubectl -n openwebui delete pvc open-webui
kubectl patch pv pvc-090fcf5b-66f0-457f-9279-f5167b075af5 \
  --type=merge -p '{"spec":{"claimRef":null}}'
kubectl -n ollama wait --for=jsonpath='{.status.phase}'=Bound pvc/open-webui \
  --timeout=90s
kubectl -n ollama rollout status statefulset/open-webui --timeout=240s
```

```text
persistentvolumeclaim "open-webui" deleted from openwebui namespace
pvc-090fcf5b-66f0-457f-9279-f5167b075af5   Released   Retain
persistentvolumeclaim/open-webui condition met
partitioned roll out complete: 1 new pods have been updated...
```

Verify Open WebUI can query Ollama and both public routes respond:

```sh
kubectl -n ollama exec open-webui-0 -- python -c \
  'import urllib.request; print(urllib.request.urlopen("http://ollama:11434/api/tags").read())'
curl -ksS -o /dev/null -w 'openwebui HTTP %{http_code}\n' \
  https://openwebui.home.tom-mendy.com/
curl -ksS -o /dev/null -w 'ollama HTTP %{http_code}\n' \
  https://ollama.home.tom-mendy.com/api/tags
```

```text
deepseek-r1:8b, gemma4:e4b, deepseek-v4-flash:cloud
openwebui HTTP 200
ollama HTTP 200
```

## Final outcome

The local Ollama chart owns both workloads, the Open WebUI ingress, and both
PVCs. `ollama.home.tom-mendy.com` continues to route to the Ollama service and
`openwebui.home.tom-mendy.com` routes to the Open WebUI service. Both PVCs use
`nfs-k8s`; no `local-path` manifest was introduced.

The tracked Git change removes the standalone Open WebUI Flux releases,
values ConfigMap, Helm source, and local extras chart. The retained PV is now
bound to `ollama/open-webui`; existing Open WebUI data remains available.

## Deferred volume reset

A request to reset the Open WebUI volume was paused before any data was
deleted. The StatefulSet was scaled to zero and then restored when the target
architecture changed to CloudNativePG and Authentik OIDC:

```text
statefulset.apps/open-webui scaled
pod/open-webui-0 condition met
partitioned roll out complete: 1 new pods have been updated...
```

The temporary reset manifest was not applied. The existing NFS PVC and its
data therefore remain intact until the PostgreSQL-backed deployment is ready.
