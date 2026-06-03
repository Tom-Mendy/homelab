# Homelab Hardening TODO

## Phase P0 - Secrets

- [x] Move committed runtime secrets to Infisical where needed.
- [x] Verify synced Kubernetes Secrets for Traefik, GitHub ARC, Newt, SearXNG,
  media VPN, Endfield, Atuin, and Keel.
- [x] Remove Grafana committed admin secret and rely on Helm-generated admin
  credentials.
- [ ] Optional: move Forgejo runner live-only Secret to Infisical.
- [x] Optional: purge/rotate old Git history secrets if this repository was
  pushed/shared while secrets were committed.
- [x] Add secret scanning CI with gitleaks or equivalent.

## Phase P1 - GitOps Reproducibility

- [x] Pin floating Helm chart `targetRevision: "*"` values to live deployed
  chart versions.
- [ ] Pin `latest` image tags to exact tags or digests.
  - [x] Pin running app images with researched exact tags and digests.
  - [ ] Pin Endfield image after CI publishes immutable tags or digest is known.
  - [ ] Review and pin Forgejo runner job image label
    `ghcr.io/catthehacker/ubuntu:act-latest`.
  - [x] Pin GitHub ARC runner image after digest is known.
  - [x] Decide whether unused Wakapi chart should be pinned or removed.
- [x] Replace remaining legacy raw manifests with chart values/templates where
  this reduces drift.
  - [x] Remove Blocky raw manifest duplicate.
  - [x] Remove Navidrome raw manifest duplicate.
  - [x] Convert Trilium raw manifest to local Helm chart.
  - [x] Remove Prometheus raw ingress/storage duplicates.
  - [x] Remove Ollama raw GPU/ingress/runtimeclass duplicates.
  - [x] Remove Keel raw ingress duplicate.
  - [x] Convert OpenWebUI raw ingress include to a local extras chart.
  - [x] Remove obsolete GitHub runner placeholder Secret.
  - [x] Review remaining raw support manifests and keep only intentional ones.
- [x] Add full Helm render/lint coverage in CI.
- [x] Add kubeconform or equivalent schema validation in CI.

## Phase P1 - Reliability Proof

- [ ] Prove backup restore for Vaultwarden.
- [ ] Prove backup restore for Forgejo.
- [ ] Prove backup restore for Grafana/Prometheus.
- [ ] Add restore automation or repeatable restore proof reports for critical
  services.
- [ ] Add minimum alerts for backup freshness, certificate expiry, PVC usage,
  NFS availability, and pod restarts/crash loops.
- [ ] Add minimum probes/resources for exposed or persistent workloads.
- [ ] Add admin ingress boundaries for exposed admin apps using native OIDC,
  Authentik proxy, IP allowlist, or an explicit accepted-risk note.
- [ ] Add NetworkPolicies for sensitive namespaces.
- [ ] Review Forgejo runner privileged Docker-in-Docker controls and document
  accepted risk or hardening plan.

## Phase P2 - Operations

- [ ] Update README/app inventory after secret and version changes.
- [ ] Document cluster rebuild from scratch.
- [ ] Add markdown lint CI or document the required `rumdl check --fix .`
  workflow.
- [ ] Add a new-app checklist covering storage, secrets, probes, resources,
  ingress auth, backups, and alerts.
- [ ] Review single-replica critical services and choose explicit accepted risk
  or HA plan.
- [ ] Review Synology NFS as central dependency and document recovery path.
- [ ] Document RTO/RPO for accepted single control-plane and NFS dependency
  risks.

## Phase P3 - Later

- [ ] Consider extra control-plane/etcd nodes if hardware budget allows.
- [ ] Benchmark NFS latency/throughput for media, Forgejo, Prometheus.
- [ ] Review MetalLB/Traefik ingress throughput and failover behavior.
