---
name: homelab-cluster
description: Administer the homelab Kubernetes cluster from Hermes, including workloads, logs, storage, Helm and Flux recovery.
---

# Homelab cluster operations

Run commands with the local terminal tool inside this workspace. Kubernetes
access is independent of the operator's computer, SSH tunnels and external
MCP servers. `KUBECONFIG=/opt/data/.kube/hermes.config` selects the dedicated
`system:serviceaccount:coder-workspaces:hermes` identity.

Available clients are `kubectl`, Helm 3, `flux` and `jq` under
`$HOME/.local/bin`. The service account has cluster-admin rights, including
Secrets, RBAC, pod execution and node operations. Never print credentials,
read the token into a prompt, copy it to the home volume or commit it.
Kubernetes rotates the mounted token, and the kubeconfig reads `tokenFile`.

## Diagnose and operate

```sh
kubectl auth whoami
kubectl auth can-i '*' '*' --all-namespaces
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.metadata.creationTimestamp
flux get all -A
helm list -A
kubectl -n <namespace> logs deployment/<name> --tail=100
kubectl -n <namespace> describe pod <name>
kubectl -n <namespace> rollout restart deployment/<name>
kubectl -n <namespace> rollout status deployment/<name> --timeout=5m
```

Flux manages the cluster from `Tom-Mendy/homelab` on Forgejo. Record durable
manifest changes in that repository. Flux can revert imperative changes;
inspect the owning HelmRelease or Kustomization before making a lasting fix.
Repository write access requires a separately authorized Forgejo identity.

The persistent home is NFS-backed and can move between node2 and node3.
All new standard PVCs must use `storageClassName: nfs-k8s`, backed by
Synology `10.0.0.11:/volume1/k8s`. Worker-local storage is forbidden.
Run `./scripts/check-storage-policy.sh` for repository changes.

## Availability and recovery

The Matrix gateway runs in the workspace and restarts after process exit.
Only the humans in `MATRIX_ALLOWED_USERS` may operate it. Keep the encrypted
Matrix configuration and allowlist enabled. Changes to the model provider
or expired model credentials can still require operator authentication.

Keep the Coder workspace started with its autostop disabled. Its home, model
configuration, Matrix crypto store and installed tools survive Pod replacement.
The NFS server, Kubernetes API and a worker must remain available.

Inspect `~/logs/gateway-coder.log` and `hermes gateway status` for gateway
failures. Coder starts its supervisor during workspace startup; a manual
`hermes gateway stop` is temporary while that supervisor runs. Stop the
workspace to shut down the gateway intentionally.

Node drains are maintenance operations. Drain only one worker at a time,
check replacement workloads and their data, then uncordon before moving on.
Do not drain the worker hosting this workspace from its own terminal, because
Pod eviction interrupts the command. Use an independent administrator session.
