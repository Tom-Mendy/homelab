# Fix qBittorrent Bad Gateway

## Problem

`https://qbittorrent.home.tom-mendy.com/` returned `Bad Gateway` from Traefik
even though the qBittorrent pod was `2/2 Running`.

## Reasoning and Commands

Check the Kubernetes routing path:

```sh
kubectl get svc,endpoints,endpointslice -n media | rg 'qbittorrent|NAME'
kubectl get svc -n media qbittorrent -o yaml
kubectl get endpoints -n media qbittorrent -o yaml
```

The Service and Endpoint pointed to the qBittorrent pod on port `8080`.

Test from inside the cluster:

```sh
kubectl run -n media curl-qbit-test --rm -i --restart=Never \
  --image=curlimages/curl:8.11.1 --command -- \
  sh -c 'curl -sv --max-time 10 http://qbittorrent.media.svc.cluster.local:8080/'
```

Initial result:

```text
Connection refused
```

Inspect the container:

```sh
kubectl exec -n media deploy/qbittorrent -c qbittorrent -- \
  sh -c 'ps auxww; netstat -ltnp'
```

The `qbittorrent-nox` process was not listening on `8080`. The container stayed
alive because s6 was running, so Kubernetes showed the pod as healthy even
though the WebUI backend was down.

The qBittorrent app log showed a tight start/stop loop:

```sh
kubectl exec -n media deploy/qbittorrent -c qbittorrent -- \
  tail -120 /config/qBittorrent/logs/qbittorrent.log
```

Useful result:

```text
qBittorrent v5.2.1 started
qBittorrent termination initiated
qBittorrent is now ready to exit
```

The profile also had a stale WebUI bind value. It was changed live from `*` to
`0.0.0.0`:

```sh
kubectl exec -n media deploy/qbittorrent -c qbittorrent -- \
  sh -c 'sed -i "s/^WebUI\\\\Address=.*/WebUI\\\\Address=0.0.0.0/" /config/qBittorrent/qBittorrent.conf'
```

That alone did not fix `5.2.1_v2.0.12`. A temporary wrapper using
`--daemon` was also tested and rejected because it was more brittle than the
image entrypoint.

Check available linuxserver qBittorrent tags:

```sh
curl -fsSL 'https://registry.hub.docker.com/v2/repositories/linuxserver/qbittorrent/tags?page_size=50&ordering=last_updated' |
  jq -r '.results[] | [.name,.last_updated,.digest] | @tsv' | head -40
```

The current stable manifest was:

```text
5.2.2 sha256:abbf2aeeb58b641977a012d0ab69939eb277cb827078450b142f782b1cd6893c
```

## Changes

Patched the live Deployment to remove the temporary command override and use
the pinned `5.2.2` image:

```sh
kubectl patch deployment -n media qbittorrent --type=json \
  -p='[
    {"op":"remove","path":"/spec/template/spec/containers/1/command"},
    {"op":"replace","path":"/spec/template/spec/containers/1/image","value":"lscr.io/linuxserver/qbittorrent:5.2.2@sha256:abbf2aeeb58b641977a012d0ab69939eb277cb827078450b142f782b1cd6893c"}
  ]'
```

Updated Git:

```text
kubernetes/media/values.yaml
```

## Verification

Rollout:

```sh
kubectl rollout status -n media deploy/qbittorrent --timeout=240s
```

Result:

```text
deployment "qbittorrent" successfully rolled out
```

Process and listener:

```sh
kubectl exec -n media deploy/qbittorrent -c qbittorrent -- \
  sh -c 'ps auxww | grep -E "[q]bittorrent|PID"; netstat -ltnp | grep 8080'
```

Useful result:

```text
/app/qbittorrent-nox --webui-port=8080
0.0.0.0:8080 LISTEN
```

Cluster Service:

```sh
kubectl run -n media curl-qbit-test --rm -i --restart=Never \
  --image=curlimages/curl:8.11.1 --command -- \
  sh -c 'curl -sv --max-time 10 http://qbittorrent.media.svc.cluster.local:8080/'
```

Result:

```text
HTTP/1.1 200 OK
qBittorrent WebUI
```

External URL through Traefik:

```sh
curl -k -sv --resolve qbittorrent.home.tom-mendy.com:443:192.168.1.20 \
  --max-time 15 https://qbittorrent.home.tom-mendy.com/
```

Result:

```text
HTTP/2 200
qBittorrent WebUI
```

Storage policy:

```sh
./scripts/check-storage-policy.sh
```

Expected:

```text
storage policy ok
```

## Outcome

qBittorrent now serves the WebUI through the ClusterIP Service and through
Traefik. The `Bad Gateway` was caused by the backend process not listening on
`8080`, not by the Ingress or Service definitions.
