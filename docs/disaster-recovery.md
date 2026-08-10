# Disaster Recovery

## Recovery objectives

- Restore the Kubernetes control plane and workers.
- Restore Synology NFS access and the `nfs-k8s` provisioner.
- Restore Forgejo, Flux Operator, Flux, and application workloads.

## Single-service failure

Inspect Flux and workload status:

```bash
kubectl -n flux-system get gitrepositories,kustomizations,helmreleases
kubectl get pods -A
```

Fix desired state in Git. To request an immediate retry without the Flux CLI:

```bash
kubectl -n flux-system annotate helmrelease <name> \
  reconcile.fluxcd.io/requestedAt="$(date +%s)" --overwrite
```

## Node failure

1. Recover node OS and network access.
2. Confirm the remaining nodes and NFS storage are healthy.
3. Check that evicted workloads reschedule on another worker.
4. Reconcile failed Flux resources after the node returns.

```bash
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get pvc,pv -A
kubectl -n flux-system get helmreleases
```

## Full cluster rebuild

The Git source is the in-cluster Forgejo service. Flux cannot bootstrap from it
until Forgejo is restored, so keep an external repository backup.

1. Rebuild Kubernetes and restore network access.
2. Install the NFS provisioner and restore required static PV/PVC bindings from
   the storage recovery inventory.
3. Restore Forgejo and its data from Synology NFS, then confirm SSH access to the
   `homelab` repository.
4. Follow `docs/flux-gitops.md` to install Flux Operator, create the SSH pull
   Secret, and apply the `FluxInstance`.
5. Restore application data backups and wait for all HelmReleases to become
   ready.

## Post-recovery validation

```bash
kubectl get nodes -o wide
kubectl get pods -A
kubectl get svc,ingress -A
kubectl get pvc,pv -A
kubectl -n flux-system get fluxinstance,gitrepositories,kustomizations,helmreleases
```

Validate at least Homepage, Grafana, Prometheus, Forgejo, Vaultwarden, Infisical,
DNS, ingress, databases, and application data.

## Caveats

- Resource exports are not equivalent to an etcd backup.
- Secrets and Git deploy keys must be backed up securely outside Git.
- Do not replace NFS-backed PVCs with worker-local storage.
