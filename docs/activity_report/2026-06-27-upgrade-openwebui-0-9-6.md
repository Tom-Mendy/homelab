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
```

Changed:

```text
targetRevision: "6.15.0"
```

to:

```text
targetRevision: "14.8.0"
```

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
