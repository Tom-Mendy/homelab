# Homelab Hardening TODO

## Phase P0 - Secrets

- [x] Move committed runtime secrets to Infisical where needed.
- [x] Verify synced Kubernetes Secrets for Traefik, GitHub ARC, Newt, SearXNG,
      media VPN, Atuin, and Keel.
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
  - [ ] Choose a hot immutable backup target, such as Backblaze B2 or Wasabi.
  - [ ] Choose an independent cold archive target, such as AWS Glacier Deep
        Archive or OVHcloud Cold Archive.
  - [ ] Back up NAS photos and other irreplaceable data with encrypted,
        versioned restic or Kopia repositories.
  - [ ] Back up Kubernetes resources with Velero, including application data
        exports and database dumps where required.
  - [ ] Define a quarterly restore test with checksum verification and an
        application recovery check.
- [ ] Add minimum alerts for backup freshness, certificate expiry, PVC usage,
      NFS availability, and pod restarts/crash loops.
- [ ] Add minimum probes/resources for exposed or persistent workloads.
- [ ] Add admin ingress boundaries for exposed admin apps using native OIDC,
      Authentik proxy, IP allowlist, or an explicit accepted-risk note.
- [ ] Add NetworkPolicies for sensitive namespaces.
- [ ] Review Forgejo runner privileged Docker-in-Docker controls and document
      accepted risk or hardening plan.

## Phase P2 - Operations

- [x] Update the README and portfolio summary after secret and version changes.
- [ ] Document cluster rebuild from scratch.
- [x] Document the required `rumdl check --fix .` workflow.
- [ ] Add a new-app checklist covering storage, secrets, probes, resources,
      ingress auth, backups, and alerts.
- [ ] Review single-replica critical services and choose explicit accepted risk
      or HA plan.
- [ ] Review Synology NFS as central dependency and document recovery path.
- [ ] Document RTO/RPO for accepted single control-plane and NFS dependency
      risks.
- [ ] Plan the migration away from Synology-specific services.
  - [ ] Evaluate Immich for photo management.
  - [ ] Evaluate OpenCloud for file management.
  - [ ] Evaluate Syncthing for device synchronization.

## Phase P2 - Public repository cleanup

- [x] Remove personal activity reports, backlogs, Hermes planning material, and
      the network migration scratchpad from the current tree.
- [x] Remove the unused public export and anonymization workflow.
- [x] Remove the duplicate GitHub validation workflow and keep Forgejo Actions
      as the repository CI.
- [x] Keep intentionally public service domains and live architecture values.
- [x] Decide not to rewrite Git history. Removed files remain available in old
      commits.

## Phase P3 - Later

- [x] Migrate Forgejo from SQLite to CloudNativePG before runner autoscaling.
- [ ] Install KEDA and scale Forgejo runners from the PostgreSQL job backlog.
  - [ ] Keep one job per runner with `--wait` and runner capacity set to one.
  - [ ] Set minimum and maximum runner counts and validate queue behavior.
- [ ] Consider extra control-plane/etcd nodes if hardware budget allows.
- [ ] Benchmark NFS latency/throughput for media, Forgejo, Prometheus.
- [ ] Review MetalLB/Traefik ingress throughput and failover behavior.
