# Move Open WebUI to CloudNativePG and Authentik OIDC

## Problem

Open WebUI used SQLite on its application PVC and local authentication. It
needed a durable PostgreSQL database on shared NFS storage, plus an Authentik
OIDC client managed by the existing blueprint and Infisical secret workflow.

## Reasoning path

The local Ollama chart creates a one-instance CloudNativePG cluster named
`openwebui-postgres` with `storageClass: nfs-k8s`. Open WebUI reads
`DATABASE_URL` from the CNPG-generated `openwebui-postgres-app` Secret.

The Authentik blueprint defines the Open WebUI provider, its strict callback,
and a `roles` scope mapping. `homelab-admins` receives Open WebUI's admin role;
`openwebui-users` receives its user role. The OIDC client secret is sourced
from Infisical at `/oidc` and synchronized to the `ollama` namespace.

After CloudNativePG was healthy, stop Open WebUI before clearing the old
application PVC. This removes the obsolete SQLite database and uploads without
touching the Ollama model PVC or PostgreSQL PVC.

```sh
kubectl -n flux-system patch helmrelease ollama --type=merge \
  -p '{"spec":{"suspend":true}}'
kubectl -n ollama scale statefulset/open-webui --replicas=0
kubectl -n ollama wait --for=delete pod/open-webui-0 --timeout=120s
kubectl apply -f /tmp/openwebui-volume-reset.yaml
kubectl -n ollama wait \
  --for=jsonpath='{.status.phase}'=Succeeded pod/openwebui-volume-reset \
  --timeout=180s
kubectl -n flux-system patch helmrelease ollama --type=merge \
  -p '{"spec":{"suspend":false}}'
```

## Command results

CloudNativePG provisioned a new NFS PVC and became healthy:

```text
openwebui-postgres   1   1   Cluster in healthy state
openwebui-postgres-1   Bound   10Gi   nfs-k8s
```

The OIDC secret was synchronized to the Open WebUI namespace (64 base64 bytes)
and Open WebUI started using PostgreSQL:

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
```

The reset pod completed successfully and Open WebUI returned to `Running`.
Ollama remained reachable from the pod with HTTP 200.

The first OIDC verification failed usefully:

```text
authentik discovery HTTP 404
Serializer errors {'client_secret': ['This field may not be null.']}
```

The synchronized `openwebui-oidc` Secret existed in `ollama`, but the
`authentik-oidc` Secret injected into the Authentik worker lacked
`OPENWEBUI_OIDC_CLIENT_SECRET`. The blueprint therefore received `null`.

## Final outcome

Open WebUI now uses a new NFS-backed CloudNativePG database and its old PVC has
been reset. The final Authentik fix adds the OIDC client-secret key to the
worker's synchronized Secret. After that Git change is reconciled, restart the
Authentik server and worker, then confirm:

```sh
curl -fsS \
  https://authentik.home.tom-mendy.com/application/o/openwebui/.well-known/openid-configuration
```

All persistent workloads use `nfs-k8s`; no `local-path` storage was added.
