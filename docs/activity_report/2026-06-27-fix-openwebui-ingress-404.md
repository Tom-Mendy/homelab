# Fix OpenWebUI Ingress 404

## Problem

`https://openwebui.home.tom-mendy.com/` returned Traefik's plain
`404 page not found`.

## Reasoning and Commands

Check the live OpenWebUI routing resources:

```sh
kubectl get ingress,svc,endpoints,pod -n openwebui -o wide
```

Useful result:

```text
ingress.networking.k8s.io/openwebui-ingress   openwebui.home.tom-mendy.com
service/open-webui                            8080/TCP
endpoints/open-webui                          10.233.75.46:8080
pod/open-webui-0                              1/1 Running
```

The Service and pod existed. Test the Service directly inside the cluster:

```sh
kubectl run -n openwebui curl-openwebui-test --rm -i --restart=Never \
  --image=curlimages/curl:8.11.1 --command -- \
  sh -c 'curl -sv --max-time 10 http://open-webui.openwebui.svc.cluster.local:8080/'
```

Result:

```text
HTTP/1.1 200 OK
Open WebUI
```

Inspect the Ingress backend:

```sh
kubectl describe ingress -n openwebui openwebui-ingress
```

Useful result:

```text
/   openwebui-open-webui:8080 (<error: services "openwebui-open-webui" not found>)
```

Traefik logs showed the same root cause:

```sh
kubectl logs -n traefik deploy/traefik --since=10m |
  rg -i 'openwebui|open-webui|error|warn|ingress'
```

Useful result:

```text
Cannot create service error="service not found" ingress=openwebui-ingress
namespace=openwebui serviceName=openwebui-open-webui
```

The live Service name from the current OpenWebUI chart is `open-webui`, but the
local extra Ingress chart still pointed at the old `openwebui-open-webui`
service name.

## Changes

Updated:

```text
kubernetes/openwebui/values.yaml
```

Changed the Ingress backend service from `openwebui-open-webui` to
`open-webui`.

## Verification

Storage policy:

```sh
./scripts/check-storage-policy.sh
```

Expected:

```text
storage policy ok
```

External URL through Traefik:

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

The `404 page not found` was caused by the Ingress referencing a Service that
no longer exists. The application itself was healthy and already served HTTP
200 through the current `open-webui` Service.
