# Project War Room Analysis — `Tom-Mendy/homelab`

## Executive Summary

Le repo est **déjà bien structuré pour un homelab Kubernetes sérieux** : Ansible + Kubespray pour bootstrap, Argo CD GitOps pour les apps, docs/runbooks, politique de stockage NFS, et plusieurs services utiles déjà modélisés.

Mais verdict production/sérieux : **Go avec conditions fortes**.

Les deux gros sujets à traiter avant de considérer ça “safe” :

1. **Secrets en clair dans le repo** — P0 sécurité.
2. **Reproductibilité / fiabilité incomplète** — versions flottantes, beaucoup de single-replica, backups documentés mais pas prouvés.

J’ai aussi enregistré le contexte essentiel du projet pour les prochaines fois.

---

## Michel — CTO Verdict

- **Verdict:** Go with conditions
- **Why:** très bon socle d’apprentissage et d’exploitation homelab, mais pas encore assez sûr pour exposer largement ou reconstruire sans surprise.
- **Top 3 priorities:**
  1. **P0 — Rotate + sortir tous les secrets du Git.**
  2. **P1 — Pin versions Helm/images critiques.**
  3. **P1 — Prouver backups/restore + ajouter probes/alerting minimum.**

---

## Critical Risks

1. **Secrets commités**
   - Exemples trouvés sans afficher les valeurs :
     - `kubernetes/traefik/values.yaml:5` — Cloudflare token
     - `kubernetes/github-runners/arc-github-auth-secret.yaml:10` — GitHub token
     - `kubernetes/newt/newt-creds.yaml:12` — connector secret
     - `kubernetes/grafana/grafana-admin-secret.yaml:8-9` — Grafana credentials
     - `kubernetes/media/values.yaml:18` — VPN private key
     - `kubernetes/searxng/values.yaml:34/45` — app/VPN secrets

2. **Single point of failure**
   - `node1` est seul control-plane/etcd.
   - Synology NFS est central pour la persistance.
   - Traefik, Blocky, Vaultwarden, Forgejo, etc. sont souvent single-replica.

3. **GitOps pas totalement reproductible**
   - Plusieurs `targetRevision: "*"` sur des Helm charts.
   - Plusieurs images utilisent `latest`.

- Argo CD `prune/selfHeal` + versions flottantes = risque de changement inattendu.

---

## Quick Wins

1. **Secrets**
   - Rotate Cloudflare/GitHub/VPN/Grafana/Newt/etc.
   - Remplacer par Infisical / ExternalSecrets / SOPS / SealedSecrets.
   - Purger l’historique Git si ce repo a été partagé ou poussé.

2. **Version pinning**
   - Remplacer `targetRevision: "*"` par des versions exactes.
   - Remplacer `latest` par tags fixes ou digests.

3. **Validation**
   - Installer Helm dans le runner CI.
   - Faire lint/template de tous les charts, pas seulement une subset.
   - Garder `scripts/check-storage-policy.sh`, il passe déjà : `storage policy ok`.

---

## Agent Reports

### Story Point — Coordination

- **Scope reviewed:**
  - `README.md`
  - `AGENTS.md`
  - `ansible/`
  - `kubernetes/`
  - `kubernetes/argocd/apps/`
  - `docs/`
  - `.forgejo/workflows/`

- **Agents used:**
  - Indien — MVP
  - 10x Engineer — Proof & Scale
  - The Architect
  - Rusty Guy
  - Dédé DSI
  - Le Documentaliste
  - Le Balaino
  - La Tour de Guet
  - Michel

- **Missing context:**
  - État live du cluster non vérifié avec `kubectl`.
  - Pas de test Helm complet, car `helm` n’est pas installé dans cet environnement.
  - Pas de preuve runtime des backups/restore.

- **Work breakdown:**
  - Sécurité secrets : P0
  - Reproductibilité GitOps : P1
  - Reliability/probes/backups : P1
  - Docs drift : P2
  - HA control plane : P2/P3 selon budget matériel

- **Estimated effort:** M

---

### Indien — MVP

- **Core value:**
  - Plateforme homelab Kubernetes personnelle, recoverable, GitOps-driven.
  - Le repo sert aussi de portfolio DevOps/Kubernetes.

- **What already works:**
  - Architecture claire dans `README.md:13-21`.
  - Bootstrap documented:
    - `ansible/run.sh`
    - `ansible/playbooks/install.yml`
    - `ansible/playbooks/deploy-apps.yml`
  - GitOps app-of-apps via Argo CD.
  - Politique storage claire dans `AGENTS.md`.

- **What blocks real usage:**
- Secrets en clair.
  - Pas de preuve automatisée “je peux rebuild/restore”.
  - README/docs un peu driftés par rapport aux apps réelles.

- **Features to cut/postpone:**
  - Ne pas viser HA complet tout de suite.
  - Ne pas complexifier avec trop d’outils secrets en même temps.
  - Priorité : choisir **une** stratégie secrets et l’appliquer.

- **Acceptable temporary debt:**
  - Single control-plane pour homelab.
  - Single replica sur apps non critiques.
  - GPU workload lié à `node3`.

---

### 10x Engineer — Proof & Scale

- **Unproven assumptions:**
  - “On peut restore facilement” — documenté, mais pas prouvé par CI ou rapport de test restore.
  - “NFS suffit” — correct pour reschedule worker, pas pour panne NAS.
  - “GitOps est reproductible” — faux tant qu’il y a `*`/`latest`.

- **Decisions based on opinion:**
  - HA non priorisée.
  - Exposition des services via `*.home.tom-mendy.com`.
  - Auto-update Keel sur certains services.

- **Scale risks:**
  - MetalLB L2 limite le trafic d’un service IP à un leader node.
  - NFS centralise I/O et disponibilité.
  - `node1` est SPOF control-plane/etcd.

- **Missing tests/metrics:**
  - Pas de Helm CI complet.
  - Peu de Helm tests.
  - Pas de SLO/RTO/RPO mesuré.
  - Pas de restore test automatisé.

- **Evidence required:**
  - Runbook “cluster rebuild from scratch”.
  - Restore test Vaultwarden/Grafana/Forgejo/Prometheus.
  - Alerts backup freshness + PVC usage + cert expiry.

---

### The Architect — Architecture

- **Structural strengths:**
  - Bonne séparation :
    - `ansible/` lifecycle
    - `kubernetes/` apps
    - `docs/` runbooks
  - App-of-apps Argo CD clair :
    - `ansible/roles/kubernetes/templates/argocd-root-application.yaml.j2`
    - `kubernetes/argocd/apps/`
  - Storage policy claire et testée :
    - `AGENTS.md`
    - `scripts/check-storage-policy.sh`

- **Structural problems:**
  - Mélange legacy Ansible app deployment + GitOps dans `ansible/roles/kubernetes/tasks/main.yml`.
- Certains docs ne suivent plus les apps réelles.
  - Secrets et values sensibles mélangés dans les manifests GitOps.

- **Anti-patterns:**
  - Versions flottantes dans GitOps.
  - Secrets Kubernetes en clair.
  - Host key ignore côté Argo CD repo credentials.

- **Refactor candidates:**
  - Déprécier le mode legacy progressivement.
  - Centraliser la stratégie secrets.
  - Ajouter conventions obligatoires pour chaque nouvelle app :
    - probes
    - resources
    - backup class
    - ingress auth policy
    - alerting minimum

- **Recommended architecture changes:**
  - Garder GitOps comme source principale.
  - Pin toutes les dépendances.
  - Introduire ExternalSecrets/Infisical proprement pour toutes les apps.
  - Ajouter CI chart rendering + kubeconform.

---

### Rusty Guy — Performance

- **Likely hotspots:**
  - NFS Synology pour tous les PVC.
  - Traefik single replica.
  - Blocky single replica.
  - Ollama GPU bound sur `node3`.

- **Complexity risks:**
  - VPN containers avec `/dev/net/tun`.
  - Forgejo runner Docker-in-Docker privilégié.
  - Media stack + NFS + VPN peut devenir fragile.

- **Memory/CPU/I/O risks:**
  - Peu de `resources.requests/limits` complets.
  - NFS peut limiter Forgejo/media/Prometheus selon charge.
  - Prometheus peut grossir vite si retention non maîtrisée.

- **Benchmark needed:**
  - Latence NFS.
  - Débit ingress Traefik.
  - Temps restore Vaultwarden/Forgejo.
  - CPU/memory baseline par namespace.

- **Optimizations worth doing now:**
  - Pas d’optimisation prématurée.
  - Priorité : observabilité + limites ressources + backups.

---

### Dédé DSI — Security

- **Critical vulnerabilities:**
  - Secrets réels probablement commités.
  - Cloudflare/GitHub/VPN/admin passwords doivent être considérés compromis.

- **Dangerous practices:**
  - Secrets dans `values.yaml`/`Secret.yaml`.
  - Apps admin exposées par ingress sans preuve de forward-auth/IP allowlist.
  - `NET_ADMIN` + `/dev/net/tun` pour VPN workloads.
- Docker-in-Docker privilégié pour Forgejo runner.

- **Attack surface:**
  - Traefik LoadBalancer.
  - Blocky DNS LoadBalancer.
  - Forgejo SSH ingress.
  - Vaultwarden, Grafana, Prometheus, Keel, Authentik, Forgejo.

- **Required fixes before production:**
  1. Rotate secrets.
  2. Remove secrets from Git.
  3. Add ingress auth/default deny for admin apps.
  4. Add NetworkPolicies for sensitive namespaces.
  5. Lock runner privileges as much as possible.

- **Risk level:** Critical until secrets are rotated.

---

### Le Documentaliste — Sources

- **Kubernetes storage:**
  - NFS/RWX is valid for shared persistent volumes.
  - Repo aligns with this via `nfs-k8s`.
  - But NFS HA depends on Synology/backups, not Kubernetes.

- **Kubernetes HA:**
  - Official HA patterns need multiple control-plane/etcd nodes.
  - Current inventory has one control-plane/etcd node.

- **Argo CD sync waves:**
  - Lowest wave first.
  - `nfs-provisioner` wave `-1` before Traefik wave `0` is correct.

- **Argo CD automated sync:**
  - `prune/selfHeal` is valid.
  - Risky with floating revisions.

- **MetalLB L2:**
  - One leader node receives traffic for a service IP.
  - Bandwidth/failover is node-bound.

---

### Le Balaino — DevOps

- **Manual processes:**
  - Secrets creation/rotation mostly manual.
  - Backups documented but not automated/proven.
  - Helm validation not complete.

- **Missing automation:**
  - Full Helm lint/template for all charts.
  - kubeconform/kubeval on rendered manifests.
  - secret scanning in CI.
  - backup/restore verification.

- **Build/test/deploy status:**
  - `scripts/check-storage-policy.sh` passes.
  - `.forgejo/workflows/storage-policy.yml` exists.
  - `kubernetes/test-helm-chart.sh` only tests a subset and does not fully gate all active charts.
  - In this environment Helm is missing.

- **Infrastructure/IaC status:**
  - Ansible + Kubespray bootstrap exists.
  - Argo CD app-of-apps exists.
- Some upstream chart versions are floating.

- **Automation quick wins:**
  1. Add Helm install in CI.
  2. Render all `kubernetes/*/Chart.yaml`.
  3. Add `kubeconform`.
  4. Add secret scanner.
  5. Add markdown lint using `rumdl check --fix .`.

---

### La Tour de Guet — SRE

- **Availability risks:**
  - Single control-plane/etcd.
  - Single Synology NFS backend.
  - Many single-replica apps.
  - Traefik ACME state makes HA trickier.

- **Observability gaps:**
  - Grafana/Prometheus exist.
  - But ServiceMonitor/PodMonitor/alerts are incomplete.
  - No alert rules found for backup freshness, cert expiry, NFS health, pod restarts.

- **Health checks:**
  - Some apps have probes.
  - Many do not: Vaultwarden, Forgejo, Grafana, Prometheus, media apps, Blocky, Homepage, Keel.

- **Backup/recovery:**
  - Docs exist:
    - `docs/backup-procedures.md`
    - `docs/disaster-recovery.md`
  - But no automated restore proof.

- **Alerts/runbooks:**
  - Runbooks are a good start.
  - Need alerting connected to the runbooks.

- **Long-term risk:**
  - The cluster can probably survive worker loss better than before thanks to NFS.
  - It cannot survive `node1`/NAS loss without manual recovery.

---

## Productive Conflicts

| Topic | Conflict | Michel decision |
|---|---|---|
| Ship fast vs security | Indien says the homelab is useful now; Dédé blocks because secrets are exposed. | Dédé wins. Rotate/remove secrets first. |
| HA control-plane | SRE wants multi-control-plane; Indien says overkill for homelab. | Accepted debt for now, but document RTO/RPO. |
| Auto-update | Balaino likes automation; 10x warns reproducibility is broken. | Pin critical services; allow auto-update only for non-critical apps. |
| NFS | Architect likes worker-independent storage; Rusty says NAS is SPOF. | Keep NFS, but add off-NAS backups and restore tests. |
| Observability | Tour de Guet wants full alerts; Indien wants MVP. | Minimum viable alerts now: certs, backups, PVC, pod restarts, NFS. |

---

## Roadmap

### Next 24h

- [ ] Rotate all secrets found in repo.
- [ ] Remove real secrets from manifests.
- [ ] Decide secrets strategy:
  - Infisical since it already appears in the repo, or
  - SOPS/age, or
  - ExternalSecrets.
- [ ] Replace Cloudflare token with scoped DNS-only token.
- [ ] Add `.gitignore`/policy for `.env`, real `*-secret.yaml`, private keys.

### Next 7 days

- [ ] Pin all `targetRevision: "*"` Helm charts.
- [ ] Replace `latest` images on critical apps.
- [ ] Fix docs drift in README.
- [ ] Add CI:
  - storage policy
  - Helm template all charts
  - kubeconform
  - secret scanning
  - markdown lint
- [ ] Add probes to core apps:
  - Traefik
  - Blocky
  - Vaultwarden
  - Forgejo
  - Grafana
  - Prometheus
  - Homepage
  - Keel

### Next 30 days

- [ ] Automate backups.
- [ ] Run and document restore tests.
- [ ] Add alerts:
  - cert expiry
  - backup freshness
  - PVC usage
  - NFS availability
  - pod crash loops
  - DNS/Traefik error rates
- [ ] Add NetworkPolicies for sensitive namespaces.
- [ ] Decide if control-plane HA is worth it before Talos migration.
- [ ] Create “new app checklist” enforced by CI.

---

## Accepted Debt

- Single control-plane for now.
- Single replica for non-critical homelab apps.
- Ollama tied to GPU node.
- Some manual recovery steps while learning.

---

## Rejected Debt

- Secrets in Git.
- Floating versions on critical infrastructure.
- No restore proof for services with important data.
- Admin apps exposed without explicit auth/network boundary.
- Adding new persistent workloads without `nfs-k8s` or documented exception.

---

## Final Decision

Le projet est **bon et très exploitable comme homelab DevOps/Kubernetes**, mais la prochaine étape doit être une passe **sécurité + reproductibilité**, pas l’ajout de nouvelles apps.

Ordre recommandé :

1. **Secrets**
2. **Pin versions**
3. **CI validation**
4. **Backups/restore**
5. **Probes/alerts**
6. Ensuite seulement : nouvelles apps ou migration Talos.
