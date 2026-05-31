# Debug SearXNG WireGuard Key

## Problem

After SearXNG restarted, the pod `searxng-59fb74465-dqkld` failed startup
checks and the `gluetun` container entered `CrashLoopBackOff`.

## Reasoning

The failing pod was inspected without printing secret values.

```sh
kubectl describe pod -n searxng searxng-59fb74465-dqkld
kubectl logs -n searxng searxng-59fb74465-dqkld -c gluetun --previous
kubectl get infisicalstaticsecret -n searxng searxng-secrets \
  -o jsonpath='{.status.conditions[?(@.type=="secrets.infisical.com/LastReconcileStatus")].status}{"\t"}{.status.conditions[?(@.type=="secrets.infisical.com/LastReconcileStatus")].message}{"\n"}'
kubectl get secret -n searxng searxng-vpn-secret -o json \
  | jq -r '
      .data.WIREGUARD_PRIVATE_KEY
      | @base64d
      | {
          length: length,
          matches_wireguard: test("^[A-Za-z0-9+/]{43}=$"),
          has_equal: contains("=")
        }
      | @json
    '
```

Observed safe output:

```text
ERROR VPN settings: Wireguard settings: private key is not valid:
wgtypes: failed to parse base64-encoded key: illegal base64 data at input byte 0

True    Reconciliation successful
{"length":55,"matches_wireguard":false,"has_equal":true}
```

## Outcome

The Infisical sync is healthy, but the current `WIREGUARD_PRIVATE_KEY` value for
SearXNG is not a valid WireGuard private key. A WireGuard private key should be
a single raw base64 string, usually 44 characters and ending with `=`.

The image digest pin was not the root cause: the new pod is using the same
Gluetun digest that was observed from the previously running pod.

## Next Commands

After correcting `WIREGUARD_PRIVATE_KEY` in Infisical path `/searxng`, run:

```sh
kubectl annotate infisicalstaticsecret -n searxng searxng-secrets \
  force-sync="$(date +%s)" --overwrite
kubectl rollout restart deploy/searxng -n searxng
kubectl rollout status deploy/searxng -n searxng
kubectl get pod -n searxng -l app=searxng
```
