# Argo CD To Flux Benchmark And Migration Backlog

## Goal

Benchmark the current Argo CD GitOps model against plain Flux CD and Flux
Operator-managed Flux before choosing a migration target.

This backlog is planning only. Do not implement Flux manifests, delete Argo CD,
or run cluster changes from this file alone.

## Current State

- Argo CD is the current GitOps controller.
- Argo CD applications live under `kubernetes/argocd/apps/`.
- Current inventory has 32 Argo CD `Application` manifests.
- Repository source used by the applications:
  `ssh://git@forgejo.forgejo.svc.cluster.local/Tom-Mendy/homelab.git`.
- Application styles in use:
  - local Helm charts from this repository;
  - external Helm charts with values files from this repository;
  - Argo CD multi-source applications using `$values`;
  - sync waves through `argocd.argoproj.io/sync-wave`;
  - automated sync with prune and self-heal;
  - namespace creation through `CreateNamespace=true`.

Storage policy remains mandatory for any later Kubernetes change:

- Do not use `local-path`.
- Use `storageClassName: nfs-k8s` for standard PVCs.
- Run `./scripts/check-storage-policy.sh` before finishing Kubernetes changes.

## Source Notes

- Flux bootstrap installs Flux controllers and configures Git sync:
  <https://fluxcd.io/flux/installation/>
- Flux bootstrap supports Forgejo through Gitea-compatible commands:
  <https://fluxcd.io/flux/installation/bootstrap/gitea/>
- Generic Flux bootstrap supports SSH Git repositories:
  <https://fluxcd.io/flux/installation/bootstrap/generic-git-server/>
- Flux Operator can install Flux through Helm, Terraform, CLI, or `kubectl`:
  <https://fluxoperator.dev/docs/guides/install/>
- Flux Operator `FluxInstance` manages Flux distribution and components:
  <https://fluxoperator.dev/docs/crd/fluxinstance/>
- Flux Operator `ResourceSet` can define app bundles and dependencies:
  <https://fluxoperator.dev/docs/resourcesets/app-definition/>
- Observed latest Flux release on 2026-06-03:
  `v2.8.8`, released 2026-05-20:
  <https://github.com/fluxcd/flux2>
- Observed latest Argo CD release on 2026-06-03:
  `v3.4.3`, released 2026-05-28:
  <https://github.com/argoproj/argo-cd>

## Benchmark Candidates

### Baseline: Current Argo CD

Keep Argo CD as the baseline for comparison.

Measure:

- current controller pod count;
- idle CPU and memory;
- time from Git push to synced application;
- failure visibility in UI and CLI;
- rollback procedure;
- cluster recovery procedure;
- how sync waves behave for current apps.

### Candidate A: Plain Flux CD

Use standard Flux APIs:

- `GitRepository`
- `Kustomization`
- `HelmRepository`
- `HelmRelease`

Expected strengths:

- official Flux bootstrap path;
- fewer extra APIs than Flux Operator;
- direct mapping to Flux Toolkit CRDs;
- good fit for repository-driven GitOps.

Expected risks:

- lifecycle and upgrades handled by bootstrap and Git manifests;
- no native Argo-like web UI;
- Argo multi-source `$values` must be translated;
- dependencies must be modeled explicitly with `dependsOn`.

### Candidate B: Flux Operator-Managed Flux

Use Flux Operator to own Flux lifecycle through `FluxInstance`.

Use standard Flux APIs for normal apps. Use `ResourceSet` only where it clearly
reduces repeated app definitions or improves dependency modeling.

Expected strengths:

- declarative Flux installation and upgrades through `FluxInstance`;
- operator-managed component configuration;
- `ResourceSet` can bundle related resources and model richer dependencies;
- good fit if future multi-cluster or app-template work is likely.

Expected risks:

- more CRDs and one more operator to understand;
- smaller ecosystem than plain Flux and Argo CD;
- ResourceSet should not be overused for simple one-off apps;
- migration needs clear ownership split between Flux Operator and Flux
  controllers.

## Benchmark Matrix

Fill this table during the benchmark.

| Area | Argo CD baseline | Plain Flux | Flux Operator |
| --- | --- | --- | --- |
| Install steps | TODO | TODO | TODO |
| Controller pods | TODO | TODO | TODO |
| Extra CRDs | TODO | TODO | TODO |
| Idle CPU | TODO | TODO | TODO |
| Idle memory | TODO | TODO | TODO |
| Git push to reconcile | TODO | TODO | TODO |
| Failed sync visibility | TODO | TODO | TODO |
| Manual reconcile command | TODO | TODO | TODO |
| Rollback workflow | TODO | TODO | TODO |
| Upgrade workflow | TODO | TODO | TODO |
| Recovery from empty cluster | TODO | TODO | TODO |
| YAML files for pilot apps | TODO | TODO | TODO |
| Learning burden | TODO | TODO | TODO |
| Final score | TODO | TODO | TODO |

## Pilot App Set

Use these apps for the benchmark because they cover the repo patterns that must
survive migration.

| App | Reason |
| --- | --- |
| `blocky` | Local chart and internal DNS-critical service. |
| `traefik` | External Helm chart, repo values, and local extra manifests. |
| `prometheus` | External Helm chart plus local monitoring extras. |
| `infisical-postgres` | Dependency-sensitive local database workload. |
| `homepage` | User-facing service metadata and Argo CD links to update later. |

## Argo CD To Flux Mapping

| Current Argo CD concept | Flux equivalent |
| --- | --- |
| `Application` with local chart path | `GitRepository` plus `HelmRelease` |
| `Application` with raw manifests | `GitRepository` plus `Kustomization` |
| External chart source | `HelmRepository` plus `HelmRelease` |
| `targetRevision` for chart | `HelmRelease.spec.chart.spec.version` |
| `destination.namespace` | target namespace on `Kustomization` or `HelmRelease` |
| `CreateNamespace=true` | explicit `Namespace` or Helm target namespace creation |
| `automated.prune=true` | `prune: true` on `Kustomization` |
| `automated.selfHeal=true` | Flux drift correction through reconcile loop |
| sync wave annotation | `dependsOn` between `Kustomization` and `HelmRelease` |
| `$values` multi-source values | inline values or ConfigMap/Secret `valuesFrom` |

## Benchmark Procedure

Run this work in a separate branch.

1. Record current Argo CD baseline.
   - Count controller pods.
   - Record idle CPU and memory.
   - Trigger one harmless Git change and measure reconcile delay.
   - Record current app health and sync status.

2. Build plain Flux pilot manifests.
   - Create test-only manifests outside active Argo CD ownership.
   - Convert only the five pilot apps.
   - Preserve chart versions and values.
   - Model ordering with `dependsOn`.
   - Keep Argo CD authoritative while manifests are reviewed.

3. Build Flux Operator pilot manifests.
   - Define `FluxInstance` with the default required controllers:
     `source-controller`, `kustomize-controller`, `helm-controller`, and
     `notification-controller`.
   - Convert the same five pilot apps.
   - Use `ResourceSet` only for cases where it removes real duplication or
     improves dependency clarity.

4. Run comparison.
   - Install only one candidate at a time, or isolate candidates so they do not
     reconcile the same app simultaneously.
   - Measure the matrix fields.
   - Record failed commands and fixes.
   - Do not migrate production ownership during the benchmark.

5. Choose target.
   - Pick plain Flux if the benchmark favors simplicity and lower moving parts.
   - Pick Flux Operator if lifecycle management and ResourceSet value outweigh
     extra operator complexity.
   - Keep Argo CD if neither candidate improves operations enough.

## Migration Plan After Benchmark

Do this only after the benchmark produces a winner.

1. Create final Flux directory structure.
   - Suggested path: `kubernetes/flux/`.
   - Keep bootstrap/lifecycle manifests separate from app manifests.
   - Keep app manifests grouped by dependency wave.

2. Convert all Argo CD applications.
   - Preserve chart versions.
   - Preserve Helm values.
   - Preserve namespace ownership.
   - Preserve dependency order from sync waves.
   - Add explicit dependencies for CRDs, databases, operators, and ingress.

3. Run static validation.
   - `./scripts/test-helm-chart.sh`
   - `./scripts/kubeconform-local-charts.sh`
   - `./scripts/check-storage-policy.sh`
   - `rumdl check --fix .`

4. Install chosen Flux target beside Argo CD.
   - Do not let both controllers own the same app at the same time.
   - Keep Argo CD authoritative until each app handoff starts.
   - Write an activity report under `docs/activity_report/` for cluster work.

5. Migrate apps by wave.
   - Wave 0: CRDs and platform base, including `traefik` and
     `cloudnative-pg`.
   - Wave 1: database foundations.
   - Wave 2: operators and secret integration.
   - Wave 3: core services such as `blocky`, `nfs-provisioner`, and
     `prometheus`.
   - Wave 4: user data apps such as `vaultwarden`, `navidrome`, `media`,
     `trilium`, and `atuin`.
   - Wave 5: AI/search/document apps such as `ollama`, `openwebui`,
     `searxng`, and `stirling-pdf`.
   - Wave 6: CI runners and Forgejo runner services.
   - Wave 8: GitHub runner scale sets.

6. Handoff each app safely.
   - Confirm app is healthy under Argo CD.
   - Suspend or remove Argo CD app ownership for that app.
   - Enable Flux ownership.
   - Wait for Flux readiness.
   - Confirm workloads, services, ingress, PVCs, and secrets.
   - Record command output in activity report.

7. Update repo docs and dashboards.
   - Replace Argo CD operational docs with Flux commands.
   - Update `docs/disaster-recovery.md`.
   - Update `docs/backup-procedures.md`.
   - Update `docs/network-diagram.md`.
   - Update homepage service link from Argo CD to chosen Flux UI or remove it.
   - Replace or retire Grafana Argo CD dashboard.

8. Remove Argo CD.
   - Remove Argo CD manifests only after all apps are Flux-owned and healthy.
   - Run one recovery drill before uninstall.
   - Keep backup of Argo CD app manifests until rollback window ends.

## Acceptance Criteria

Benchmark acceptance:

- Matrix is filled with measured values.
- All five pilot apps have working plain Flux manifests.
- All five pilot apps have working Flux Operator manifests, unless the operator
  path fails early for a documented reason.
- One target is chosen with written reasoning.
- No production app ownership changed by benchmark alone.

Migration acceptance:

- All former Argo CD apps reconcile under chosen Flux target.
- No active app is reconciled by Argo CD and Flux at the same time.
- `./scripts/check-storage-policy.sh` passes.
- No active manifest under `kubernetes/` uses `local-path`.
- New persistent workloads can reschedule between `node2` and `node3`.
- Activity reports exist for real Kubernetes work.
- Argo CD removal happens only after recovery drill succeeds.

## Open Questions For Benchmark

- Does plain Flux give enough observability without a dedicated UI?
- Does Flux Operator reduce enough lifecycle work to justify another operator?
- Is `ResourceSet` useful for repeated runner apps, or is plain
  `HelmRelease` clearer?
- Should future GitOps state remain Git-based, or should OCI artifacts be tested
  later for recovery and supply-chain hardening?
