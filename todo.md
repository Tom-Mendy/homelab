# Homelab Hardening TODO

## Phase P0 - Secrets

- [x] Move committed runtime secrets to Infisical where needed.
- [x] Verify synced Kubernetes Secrets for Traefik, GitHub ARC, Newt, SearXNG,
  media VPN, Endfield, Atuin, and Keel.
- [x] Remove Grafana committed admin secret and rely on Helm-generated admin
  credentials.
- [ ] Optional: move Forgejo runner live-only Secret to Infisical.
- [X] Optional: purge/rotate old Git history secrets if this repository was
  pushed/shared while secrets were committed.

## Phase P1 - GitOps Reproducibility

- [x] Pin floating Helm chart `targetRevision: "*"` values to live deployed
  chart versions.
- [ ] Pin `latest` image tags to exact tags or digests.
  - [x] Pin running app images with researched exact tags and digests.
  - [ ] Pin Endfield image after CI publishes immutable tags or digest is known.
  - [x] Pin GitHub ARC runner image after digest is known.
  - [x] Decide whether unused Wakapi chart should be pinned or removed.
- [ ] Replace remaining legacy raw manifests with chart values/templates where
  this reduces drift.
- [ ] Add full Helm render/lint coverage in CI.
- [ ] Add kubeconform or equivalent schema validation in CI.

## Phase P1 - Reliability Proof

- [ ] Prove backup restore for Vaultwarden.
- [ ] Prove backup restore for Forgejo.
- [ ] Prove backup restore for Grafana/Prometheus.
- [ ] Add backup freshness checks/alerts.
- [ ] Add minimum probes/resources for exposed or persistent workloads.

## Phase P2 - Operations

- [ ] Update README/app inventory after secret and version changes.
- [ ] Document cluster rebuild from scratch.
- [ ] Review single-replica critical services and choose explicit accepted risk
  or HA plan.
- [ ] Review Synology NFS as central dependency and document recovery path.

## Phase P3 - Later

- [ ] Consider extra control-plane/etcd nodes if hardware budget allows.
- [ ] Benchmark NFS latency/throughput for media, Forgejo, Prometheus.
- [ ] Review MetalLB/Traefik ingress throughput and failover behavior.
