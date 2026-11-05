# Homelab — maintenance applicative du 2 novembre 2026

## Périmètre et résultat

Clôture de la vague **compatible**, pas déclaration que toutes les applications
sont à leur dernière version. Les migrations sensibles encore bloquées sont
listées séparément ci-dessous. Kubernetes, Calico et MetalLB n'ont pas été mis à
jour. Aucun PVC existant n'a été supprimé pour résoudre une stratégie de rollout.

Tous les changements actifs ont été publiés dans `main` et réconciliés par Flux.
Contrôle final de cette vague : 41 HelmReleases Ready, aucun pod non prêt, et
28 hôtes d'ingress internes interrogés avec validation TLS. Les réponses 302
et le 401 de NZBGet représentent des barrières d'authentification, pas une
connexion utilisateur interactive réussie.

## Applications et charts déployés

| Composant | Version/état final | Vérification réelle |
|---|---|---|
| Forgejo | 15.0.9 → **15.0.11 LTS**, Recreate | API version ; SSH Git ; sauvegarde DB finale restaurée en isolation |
| Forgejo Runner, quatre releases | 12.13.2 → **13.2.1** | Docker 29.8.2 préexistant ; aucun conteneur de job lors du précontrôle ; quatre Deployments prêts |
| Homepage | 1.13.2 → **2.7.0** | HTTPS 200 ; authentification native opt-in non activée ; allowedHosts conservé |
| Coder | 2.38.0 → **2.38.5** mainline | API buildinfo ; restauration de sa DB isolée ; pas de rétrogradation vers le canal Stable |
| Grafana | chart 13.5.0 → **14.3.0**, application **13.3.0** | `/api/health` : database ok ; sauvegarde SQLite intègre |
| Prometheus | chart 29.36.1 → **29.40.3**, application **3.15.1** | API buildinfo success ; rollout |
| Harbor | chart 1.19.2 → **1.19.4** | Images 2.15.4 épinglées conservées ; les huit composants de l'API health sont healthy |
| Traefik | image **3.7.17**, chart **42.2.0** | HTTPS public et interne après changement ; miroir d'image indépendant conservé |
| Authentik | **2026.8.5** | Server/worker prêts ; découverte OIDC et redirections ; pas de connexion interactive revendiquée |
| Newt | 1.18.1 → **1.19.0**, chart 1.1.0 → **1.5.0** | Singleton Recreate ; schéma validé ; accès publics rétablis |
| Infisical operator | 0.11.0 → **0.11.16** | Versions stockées des CRDs conservées ; 12 synchronisations de secrets réussies contre l'ancien serveur |
| ARC controller et deux runner sets | 0.15.0 → **0.15.1** | Sources OCI et trois releases réconciliées ; contrôleur/listeners prêts |
| Runner GitHub dotfiles | **2.338.2** | Image explicitement fixée ; distinct du runner Forgejo |
| Vaultwarden | 1.37.4 → **1.37.5**, Recreate | Rollout ; sauvegarde SQLite avec integrity_check ok |
| Atuin | 18.23.0 → **18.24.4** | Rollout et endpoint ; sauvegarde PostgreSQL |
| Ollama | 0.40.3 → **0.40.13** | Modèles/API et génération réelle ayant répondu `OK` |
| Open WebUI | 0.12.0 → **0.12.5** | Rollout ; DB et fichiers sauvegardés ; base vectorielle archivée intègre |
| Cinny | 4.12.7 → **4.12.8** | HTTPS public 200 |
| Matrix RTC LiveKit | 1.13.9 → **1.13.11** | Endpoint interne et ingress ; aucune revendication de test média public complet |
| Matrix RTC JWT | 0.8.0 → **0.9.0** | Health interne et ingress 200 ; revue du correctif de sécurité standalone |
| SearXNG | build du 22 août → **1er novembre 2026**, digest fixé | Recherche réelle : 35 résultats ; DuckDuckGo signale un CAPTCHA |
| qBittorrent | 5.2.4 → **5.3.0**, Recreate | API version ; 20 torrents et taille totale conservés ; redirection publique Authentik |
| Suivi de stage | Ancien digest fonctionnel rétabli | `/health/ready` : app/database/Garage ok ; promotion automatique suspendue |

Sonarr **4.0.20.3014**, Radarr **6.4.4.10685**, Tuwunel **1.9.4**, Blocky
**0.35.0** et Navidrome **0.64.2** correspondent aux releases officielles
vérifiées. NZBGet conserve son packaging `26.3.20260925` de la release 26.3.
CloudNativePG chart 0.29.1 et NFS provisioner 4.0.18 n'avaient pas de candidat
supplémentaire lors de la revue des index. Les images auxiliaires et majeures
PostgreSQL ne sont pas assimilées à des mises à jour applicatives automatiques.

## Incidents et limites fonctionnelles

### Newt : 503 lors d'un chevauchement d'identité

Une référence publique valide a été relevée avant la reprise. Le rollout de
1.19.0 a reproduit les 503 avec des cibles pourtant saines. Le même binaire a
retrouvé les routes publiques après arrêt complet puis démarrage exclusif : le
test isole le chevauchement de connecteurs, plutôt qu'une incompatibilité de
version démontrée. Une stratégie Recreate est maintenant persistée dans Flux.

Le chart 1.5 sépare les valeurs upstream des ressources locales Infisical, active
les probes et monte un `/tmp` writable tout en gardant le root filesystem read-only.
Les post-renderers complets et le schéma ont été validés avant déploiement.

### Suivi de stage

Le nouveau digest quittait immédiatement avec un code 0 ; l'ancien pod continuait
à servir les requêtes. Le digest fonctionnel a été restauré et l'automatisation
ImageUpdateAutomation de cette application suspendue. Un dernier commit déjà en
vol a nécessité une seconde restauration du pin après suspension observée.
La cause du build défectueux reste à corriger dans le projet applicatif avant de
réactiver sa promotion. Aucun rebuild prétendument corrigé n'a été publié.

### RTC public

`https://rtc.tom-mendy.com/healthz` renvoyait **404 via 92.222.90.223 avant** les
mises à jour RTC et renvoie encore 404 après. Le service JWT et le même hostname
via Traefik interne répondent **200**. Il reste à examiner la ressource/règle
Pangolin ou son backend public avec un accès administratif autorisé ; il ne
s'agit pas d'un test WebRTC de bout en bout réussi.

Le hostname configuré pour qBittorrent est **torrent.tom-mendy.com**. Un essai sur
`qbittorrent.tom-mendy.com`, qui n'est pas configuré, a été écarté de la couverture.
Le hostname réel répond 302 avec TLS valide via l'edge public.

## Sauvegardes et restaurations

Les artefacts sensibles ne sont pas dans Git et leurs valeurs ne sont pas
reproduites dans ce rapport.

- Sauvegardes initiales : `/opt/data/maintenance-snapshots/20261102T111528Z/`.
- Nouvelle vague : `/opt/data/maintenance-snapshots/20261102T202222Z/`.
- Préparation stateful isolée : `/opt/data/maintenance-snapshots/resume-stateful/`.
- Sauvegarde finale Forgejo : PVC `forgejo/forgejo-maintenance-backups`, répertoire
  `20261102T211509Z`, manifeste `state: complete`, 3 908 membres dans l'archive de
  fichiers, dump PostgreSQL de 1 193 186 octets et archive `/data` de 1 985 225 358
  octets. Corbeille Synology et métadonnées `@eaDir` explicitement exclues ; les
  clés SSH root-owned sont incluses. L'archive a été relue complètement.
- Le **dump final hors ligne** de Forgejo, et non seulement un dump antérieur,
  a été restauré avec pg_restore en PostgreSQL isolé ; comptes/dépôts présents.
  Coder a également subi une vraie restauration isolée. Ces tests omettent
  propriétaires/ACL et ne constituent pas un démarrage complet d'une instance
  restaurée avec fichiers/SSO.
- Les dumps Infisical et Hindsight ont été restaurés par la préparation isolée
  sur PVC NFS dédiés : respectivement 795 et 25 tables. Pas de répétition de
  migration du binaire cible, de déchiffrement Infisical ou de rappel mémoire
  Hindsight cible revendiqués.
- SQLite Grafana, Sonarr et Radarr : intégrité des copies sauvegardées `ok`.
  ZIP CRC seul n'a pas été traité comme une preuve SQLite suffisante.
- Les sauvegardes partagent le domaine de panne du NAS. Une copie indépendante
  chiffrée et la récupération des clés/configurations critiques restent à établir
  pour les migrations à risque. Aucune garantie hors site n'est revendiquée.

### Maintenance Forgejo auto-hébergée

La source GitOps étant Forgejo lui-même, le reprendre après un simple commit
supprimant son Deployment aurait dépendu d'un dépôt arrêté. Un hook Helm
pré-upgrade à usage unique a utilisé un artefact déjà téléchargé : arrêt du seul
Deployment, attente des anciens pods, sauvegarde DB + fichiers hors ligne, puis
création du Deployment Recreate cible par Helm. Les échecs d'accès initiaux à la
corbeille NAS puis aux clés SSH ont déclenché la restauration automatique du
Deployment précédent ; ils n'ont pas été contournés en supprimant des données.

Le hook est **désarmé** (`offlineUpgradeEnabled: false`). Pour le réutiliser,
préparer et déployer son code/ConfigMap avec hook désactivé d'abord : Helm exécute
les hooks avant de mettre à jour les ressources ordinaires. Précontrôler toutes
les traversées de répertoires, droits DB/API et stockage, puis préparer récupération
et fenêtre de maintenance. Ne jamais laisser le hook actif sur un chart local
réconcilié à chaque révision du dépôt. Le PVC de sauvegarde est conservé.

## Reports non forcés

| Composant | État conservé | Gate avant modification |
|---|---|---|
| Prowlarr | 2.6.5 | Les cinq archives vérifiées, dont les quatre hebdomadaires et la nouvelle manuelle, retournent `database disk image is malformed`. Décision de récupération séparée ; aucune réparation/restauration automatique de production. |
| Hindsight | API 0.10.2 / control plane 0.10.3 | Répétition de la migration 1.1.0 et des fonctions applicatives ; récupération rôles/configuration/pg0 ; sauvegarde finale et copie indépendante protégée. |
| Infisical serveur | Application 0.166.5 / chart 1.8.0 | Répétition migration/déchiffrement/authentification ; escrow chiffré des clés ; décision sur queues Redis ; arrêt exclusif et sauvegarde finale. Operator déjà validé en 0.11.16. |
| Garage | 2.4.1 | Sauvegarde complète du nœud arrêté, restauration isolée et plan de restauration complet ; la migration 2.5 interdit un downgrade sur les données migrées. |

Procédures : `kubernetes/hindsight/UPGRADE.md`, `kubernetes/infisical/UPGRADE.md`,
`kubernetes/garage/UPGRADE.md`. Leurs fichiers `maintenance/` sont des préparations
**inactives**, pas des déploiements réussis ni une autorisation de perdre des données.

## Sources principales

- <https://forgejo.org/docs/latest/admin/upgrade/>
- <https://codeberg.org/forgejo/forgejo/src/branch/forgejo/release-notes-published/15.0.11.md>
- <https://charts.fossorial.io/index.yaml>
- <https://github.com/fosrl/newt/releases/tag/1.19.0>
- <https://github.com/gethomepage/homepage/releases/tag/v2.7.0>
- <https://github.com/coder/coder/releases/tag/v2.38.5>
- <https://github.com/livekit/livekit/releases/tag/v1.13.11>
- <https://github.com/element-hq/lk-jwt-service/releases/tag/v0.9.0>
- <https://github.com/Infisical/kubernetes-operator/releases/tag/infisical-k8-operator/v0.11.16>
- <https://github.com/actions/actions-runner-controller/releases/tag/gha-runner-scale-set-0.15.1>
