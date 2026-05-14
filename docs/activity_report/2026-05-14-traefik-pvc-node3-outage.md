# Traefik PVC blocked by node3 outage

## 1. Problem to solve

Traefik was unavailable because its pod stayed `Pending`:

```text
traefik-69c7647584-zw8h8   0/1   Pending   0   2d14h
```

The cluster had three nodes, but `node3` was `NotReady` after being powered off:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" get nodes -o wide
```

Result:

```text
NAME    STATUS     ROLES           INTERNAL-IP
node1   Ready      control-plane   192.168.1.11
node2   Ready      <none>          192.168.1.12
node3   NotReady   <none>          192.168.1.13
```

Traefik used a `local-path` PVC. That PVC was physically tied to `node3`, so
Kubernetes could not reschedule Traefik to `node2`.

## 2. Reasoning path and commands

First, inspect Traefik resources:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n traefik get pods,deploy,svc,pvc -o wide
```

Useful result:

```text
pod/traefik-69c7647584-sdwlw   1/1   Terminating   node3
pod/traefik-69c7647584-zw8h8   0/1   Pending       <none>

persistentvolumeclaim/traefik  Bound  pvc-4f16151f-a4c0-4b9d-a4d4-1cfdc0a17101  local-path
```

Then inspect why the new pod could not schedule:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n traefik describe pod traefik-69c7647584-zw8h8
```

Important scheduler event:

```text
0/3 nodes are available:
1 node(s) didn't match PersistentVolume's node affinity,
2 node(s) had untolerated taint(s).
preemption: 0/3 nodes are available: 3 Preemption is not helpful for scheduling.
```

Then inspect the PV:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  get pv pvc-4f16151f-a4c0-4b9d-a4d4-1cfdc0a17101 -o yaml
```

Important result:

```yaml
spec:
  storageClassName: local-path
  hostPath:
    path: /opt/local-path-provisioner/pvc-4f16151f-a4c0-4b9d-a4d4-1cfdc0a17101_traefik_traefik
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/hostname
              operator: In
              values:
                - node3
```

This proved the core issue: the data was on `node3`, and the replacement pod
could not mount it anywhere else.

We also checked whether `node3` could be recovered remotely:

```bash
ping -c 3 192.168.1.13
ssh -o BatchMode=yes -o ConnectTimeout=5 192.168.1.13 hostname
```

Results:

```text
3 packets transmitted, 0 received, 100% packet loss
kex_exchange_identification: read: Connection reset by peer
```

That confirmed the first recovery path was physical: power `node3` back on.

## 3. Results, including failed attempts

After `node3` was powered on again:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" get nodes -o wide
```

Result:

```text
node1   Ready
node2   Ready
node3   Ready
```

Traefik recovered:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n traefik get pods,deploy,pvc -o wide
```

Result:

```text
deployment.apps/traefik   1/1
pod/traefik-...           1/1   Running   node3
persistentvolumeclaim/traefik   Bound   local-path
```

This fixed the outage, but not the root cause. If `node3` went down again,
Traefik would be blocked again.

The durable fix was to create a shared NFS storage class:

```bash
helm upgrade --install nfs-provisioner \
  nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --namespace nfs-provisioner \
  --create-namespace \
  -f kubernetes/nfs-provisioner/values.yaml \
  --kubeconfig "$HOME/.kube/config-homelab"
```

Validation:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" get storageclass nfs-k8s
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n nfs-provisioner get pods -o wide
```

Useful result:

```text
nfs-k8s   cluster.local/nfs-provisioner-nfs-subdir-external-provisioner   Retain
nfs-provisioner-...   1/1   Running
```

A smoke test PVC confirmed dynamic provisioning:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n nfs-k8s-test apply -f smoke-pvc.yaml
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n nfs-k8s-test wait --for=jsonpath='{.status.phase}'=Bound pvc/nfs-k8s-smoke
```

Result:

```text
persistentvolumeclaim/nfs-k8s-smoke condition met
```

Synology also showed the created directory under `/volume1/k8s`.

## 4. Final outcome and required changes

The final fix was to migrate Traefik from `local-path` to `nfs-k8s`.

Steps performed:

1. Temporarily paused Argo CD auto-sync for `homelab` and `traefik`.
2. Created a temporary NFS PVC:

   ```yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: traefik-nfs-migration
   spec:
     accessModes:
       - ReadWriteMany
     storageClassName: nfs-k8s
     resources:
       requests:
         storage: 128Mi
   ```

3. Scaled Traefik down:

   ```bash
   kubectl --kubeconfig "$HOME/.kube/config-homelab" \
     -n traefik scale deploy/traefik --replicas=0
   ```

4. Copied `/data/acme.json` from the old PVC to the temporary NFS PVC using a
   copy pod.

5. Deleted and recreated the final `traefik` PVC with:

   ```yaml
   storageClassName: nfs-k8s
   ```

6. Copied the data from the temporary NFS PVC into the final PVC.

7. Scaled Traefik back up and verified logs:

   ```bash
   kubectl --kubeconfig "$HOME/.kube/config-homelab" \
     -n traefik rollout status deploy/traefik
   kubectl --kubeconfig "$HOME/.kube/config-homelab" \
     -n traefik logs deploy/traefik --tail=80
   ```

Useful result:

```text
deployment "traefik" successfully rolled out
Starting provider *acme.Provider
Testing certificate renew...
```

8. Updated GitOps:

```yaml
persistence:
  enabled: true
  name: traefik-data
  accessMode: ReadWriteOnce
  storageClass: nfs-k8s
  size: 128Mi
  path: /data
```

Final state:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n traefik get pvc,pod -o wide
```

Result:

```text
persistentvolumeclaim/traefik   Bound   nfs-k8s
pod/traefik-...                 1/1     Running
```

Important lesson: `local-path` is not acceptable for critical Kubernetes
workloads in this homelab. It makes the workload depend on one worker node. The
repository now uses `nfs-k8s` for Traefik and documents that future persistent
Kubernetes workloads must avoid worker-local storage.
