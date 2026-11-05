On 2026-11-02, `https://chat.tom-mendy.com/` returned HTTP 503 with
`no available server` after cluster application updates. Cinny itself returned
HTTP 200, both inside its container and through cluster Traefik at `10.0.0.60`.

Pangolin's generated `5-chat-service` had an empty backend list. Its persisted
health check for Cinny was `unhealthy`, although Newt reported target 6 as
healthy and Cinny access logs showed successful checks every five seconds.
Other monitored targets on the same tunnel also had stale unhealthy states.

Restarting the existing Newt deployment restored health reporting:

```sh
kubectl -n newt-system rollout restart deployment/newt-newt-main-tunnel
kubectl -n newt-system rollout status deployment/newt-newt-main-tunnel
curl -fsS -o /dev/null -w '%{http_code}\n' https://chat.tom-mendy.com/
```

After reconnection, Pangolin marked Cinny and Tuwunel healthy. The public Cinny
page, its JavaScript bundle, `/config.json`, and Matrix's
`/_matrix/client/versions` endpoint all returned HTTP 200.

Newt remained on its existing pinned version 1.18.1. ReplicaSet history showed
an attempted 1.19.0 update followed by a rollback earlier that day. The exact
trigger for the stale health state was not established. If this recurs, compare
Newt's current checks with Pangolin's recorded health before changing Cinny's
image or configuration. No authenticated chat operation was tested.
