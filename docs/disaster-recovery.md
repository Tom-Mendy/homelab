# Disaster Recovery

This runbook describes how to recover the homelab after partial
or total cluster failure.

## Recovery objectives

- Restore Kubernetes control plane and worker nodes
- Restore platform services (MetalLB, Traefik, Blocky, Argo CD)
- Restore business-critical apps and data

## Prerequisites

- Access to this repository
- SSH access to all nodes (`ansible/private_key`)
- Correct inventory in `ansible/inventory.ini`
- Access to application data backups

## Recovery levels

## Level 1: Single service failure

1. Inspect Argo CD and pod status:

   ```bash
   kubectl get applications -n argocd
   kubectl get pods -A
   ```

2. If GitOps-managed, sync/fix via Argo CD by reconciling desired state in Git.
3. If needed, redeploy platform/apps:

   ```bash
   cd ansible
   ./run.sh playbooks/deploy-apps.yml
   ```

## Level 2: Node failure

1. Recover node OS/network access.
2. Validate inventory reachability:

   ```bash
   cd ansible
   ./run.sh playbooks/update.yml --check
   ```

3. Re-run app deployment to reconcile workloads:

   ```bash
   ./run.sh playbooks/deploy-apps.yml
   ```

4. Restore app data for impacted PVCs if needed.

## Level 3: Full cluster rebuild

Use when control plane/etcd is unrecoverable.

1. Recreate/repair nodes (OS + SSH + networking).
2. (Optional) reset old cluster state:

   ```bash
   cd ansible
   ./run.sh playbooks/reset.yml
   ```

3. Install Kubernetes with Kubespray:

   ```bash
   ./run.sh playbooks/install.yml
   ```

4. Deploy platform and applications:

   ```bash
   ./run.sh playbooks/deploy-apps.yml
   ```

5. Restore persistent data backups to required PVCs/services.

## Post-recovery validation

Run at minimum:

```bash
kubectl get nodes -o wide
kubectl get pods -A
kubectl get svc -A
kubectl get ingress -A
```

Validate key endpoints:

- `argocd.home.tom-mendy.com`
- `homepage.home.tom-mendy.com`
- `grafana.home.tom-mendy.com`
- `prometheus.home.tom-mendy.com`
- `forgejo.tom-mendy.com`
- `vaultwarden.home.tom-mendy.com`

## Known caveats

- `reset.yml` is destructive for Kubernetes state.
- Resource YAML exports are not equivalent to full etcd backup/restore.
- Secrets must be backed up and stored securely.
