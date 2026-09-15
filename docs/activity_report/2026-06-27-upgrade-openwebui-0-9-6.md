# Upgrade OpenWebUI to 0.9.6

## Problem

OpenWebUI showed this update notice:

```text
A new version (v0.9.6) is now available. Update for the latest features and improvements.
```

The cluster was still running:

```text
ghcr.io/open-webui/open-webui:0.6.9
```

## Reasoning and Commands

Check the live OpenWebUI image:

```sh
kubectl get sts -n openwebui open-webui \
  -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{" "}{.image}{"\n"}{end}'
```

Result:

```text
open-webui ghcr.io/open-webui/open-webui:0.6.9
```

Check the Argo CD app source:

```sh
sed -n '1,220p' kubernetes/argocd/apps/openwebui.yaml
```

The app used the upstream OpenWebUI Helm chart:

```text
chart: open-webui
targetRevision: "6.15.0"
```

Check the upstream Helm index because `helm` was not installed in this shell:

```sh
curl -fsSL https://helm.openwebui.com/index.yaml | sed -n '1,220p'
```

Useful result:

```text
appVersion: 0.9.6
urls:
- open-webui-14.8.0.tgz
version: 14.8.0
```

The smallest durable change is to bump the chart version. The chart's default
image tag is empty, which means it follows the chart `appVersion`.

## Changes

Updated:

```text
kubernetes/argocd/apps/openwebui.yaml
kubernetes/openwebui/values.yaml
kubernetes/openwebui/values.schema.json
kubernetes/openwebui/templates/pvc.yaml
```

Changed:

```text
targetRevision: "6.15.0"
```

to:

```text
targetRevision: "14.8.0"
```

The `14.8.0` chart changed the generated resource name from `open-webui` to
`openwebui-open-webui`. The first sync started a fresh PVC:

```text
persistentvolumeclaim/openwebui-open-webui   Bound   nfs-k8s
```

The previous data PV was retained:

```sh
kubectl get pv -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,CLAIM:.spec.claimRef.namespace/.spec.claimRef.name,SC:.spec.storageClassName,RECLAIM:.spec.persistentVolumeReclaimPolicy,PATH:.spec.nfs.path |
  rg 'openwebui|open-webui|NAME'
```

Useful result:

```text
pvc-090fcf5b-66f0-457f-9279-f5167b075af5   Released   openwebui/open-webui   nfs-k8s   Retain   /volume1/k8s/openwebui-open-webui-pvc-090fcf5b-66f0-457f-9279-f5167b075af5
```

To keep the old names and data, the OpenWebUI values now set:

```yaml
fullnameOverride: open-webui

persistence:
  existingClaim: open-webui
```

The old chart had websocket support disabled by default. The new chart enables
websocket Redis by default, so the merged values explicitly keep it disabled:

```yaml
websocket:
  enabled: false
```

The local OpenWebUI extras chart also manages the `open-webui` PVC with
`volumeName: pvc-090fcf5b-66f0-457f-9279-f5167b075af5`.

The retained PV was rebound live before the final sync:

```sh
kubectl patch pv pvc-090fcf5b-66f0-457f-9279-f5167b075af5 --type=json \
  -p='[{"op":"remove","path":"/spec/claimRef"}]'

kubectl apply -f - <<'YAML'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: open-webui
  namespace: openwebui
  annotations:
    argocd.argoproj.io/sync-options: Prune=false
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: nfs-k8s
  volumeName: pvc-090fcf5b-66f0-457f-9279-f5167b075af5
YAML
```

Result:

```text
persistentvolume/pvc-090fcf5b-66f0-457f-9279-f5167b075af5 patched
persistentvolumeclaim/open-webui created
```

The previous upstream chart values file was merged into the local chart values:

```text
kubernetes/openwebui/openwebui-values.yaml -> kubernetes/openwebui/values.yaml
```

Argo CD now passes the single merged values file to the upstream OpenWebUI Helm
chart:

```text
$values/kubernetes/openwebui/values.yaml
```

The local chart schema now allows extra top-level keys because the same values
file is shared by both the local extras chart and the upstream OpenWebUI chart.

## Verification

Storage policy:

```sh
./scripts/check-storage-policy.sh
```

Expected:

```text
storage policy ok
```

After sync, verify the image:

```sh
kubectl get sts -n openwebui open-webui \
  -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{" "}{.image}{"\n"}{end}'
```

Expected:

```text
open-webui ghcr.io/open-webui/open-webui:0.9.6
```

Verify the PVC is the retained NFS PV:

```sh
kubectl get pvc -n openwebui open-webui -o jsonpath='{.spec.volumeName}{"\n"}'
```

Expected:

```text
pvc-090fcf5b-66f0-457f-9279-f5167b075af5
```

Verify the public URL:

```sh
curl -k -sv --resolve openwebui.home.tom-mendy.com:443:192.168.1.20 \
  --max-time 15 https://openwebui.home.tom-mendy.com/
```

Expected:

```text
HTTP/2 200
Open WebUI
```

## Outcome

OpenWebUI is managed by the upstream Helm chart through Argo CD. Updating the
chart to `14.8.0` updates the application image to OpenWebUI `0.9.6`.
