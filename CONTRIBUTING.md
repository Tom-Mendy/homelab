# Contributing

Thanks for taking the time to improve the project.

## Before opening a change

- Keep code and documentation in English.
- Do not commit credentials, tokens, private keys, kubeconfig files, or real
  environment-specific secrets.
- Use `storageClassName: nfs-k8s` for standard persistent volumes. Never add
  `local-path` for a Kubernetes workload.
- Pin container images and Helm chart versions when the workload is deployed
  by Flux.
- Add or update documentation when a change alters recovery, storage, secrets,
  or operational behavior.

## Local checks

```bash
./scripts/check-storage-policy.sh
./scripts/test-helm-chart.sh
./scripts/render-local-charts-for-kubeconform.sh
rumdl check README.md CONTRIBUTING.md SECURITY.md \
  docs/architecture.md docs/portfolio-summary.md docs/publication.md
```

If a change affects rendered Kubernetes resources, also run kubeconform against
the generated files.

## Pull requests

Explain the operational reason for the change, the affected workloads, and the
validation that was performed. For stateful services, include the backup and
rollback considerations.
