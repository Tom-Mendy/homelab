# Kubeconfig for a non-root user

Run on a control-plane node to copy the admin kubeconfig to the current user.

```bash
mkdir -p "$HOME/.kube"
sudo cp /etc/kubernetes/admin.conf "$HOME/.kube/config"
sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config"
chmod 600 "$HOME/.kube/config"
```

## Use `kubectl` locally against `10.0.0.21`

Run these commands on your local machine.

```bash
mkdir -p "$HOME/.kube"
scp <user>@10.0.0.21:/etc/kubernetes/admin.conf "$HOME/.kube/config-homelab"
chmod 600 "$HOME/.kube/config-homelab"

# Ensure kubectl points to the reachable control-plane IP.
# The current API certificate contains the DNS name node1, so keep that TLS name
# while connecting to the new IP.
CTX=$(kubectl --kubeconfig "$HOME/.kube/config-homelab" config current-context)
CLUSTER=$(kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  config view \
  -o jsonpath="{.contexts[?(@.name==\"$CTX\")].context.cluster}")
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  config set-cluster "$CLUSTER" \
    --server=https://10.0.0.21:6443 \
    --tls-server-name=node1
```

Use it one-off:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" get nodes
```

Or set it for your current shell session:

```bash
export KUBECONFIG="$HOME/.kube/config-homelab"
kubectl get nodes
```

Optional: rename the context for clarity.

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  config rename-context kubernetes-admin@kubernetes homelab-admin
kubectl --kubeconfig "$HOME/.kube/config-homelab" config use-context homelab-admin
```
