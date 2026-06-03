• Oui, possible. Mais pas avec simple replicaCount: 1..5 sur même runner secret: ça clone même identité runner, risque conflit.

  Best path:

  1. Migrer Forgejo SQLite -> CloudNativePG.
  2. Installer KEDA.
  3. Créer ScaledObject min 1, max 5, trigger PostgreSQL:
      - query queue Forgejo: jobs status=5 + runs_on contient ubuntu-latest
      - scale runner Deployment selon backlog

  4. Garder one-job --wait, capacity: 1.

  Pourquoi PG d’abord: KEDA a scaler PostgreSQL natif; SQLite non. Cluster a HPA, mais pas KEDA actuellement.

  Docs:

  - KEDA PostgreSQL scaler: https://keda.sh/docs/latest/scalers/postgresql/
  - Forgejo ephemeral runner: https://forgejo.org/docs/v15.0/admin/actions/security/

  J’ai arrêté le changement “5 statiques”. Working tree restant: backlog PG seulement.
