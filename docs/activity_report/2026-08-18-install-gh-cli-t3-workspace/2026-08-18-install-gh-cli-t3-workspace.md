# Installation de GitHub CLI dans le workspace T3

## Problème

Le workspace T3 devait fournir la commande `gh` pour utiliser GitHub depuis le
terminal et les agents Codex.

## Modification

Le startup script installe GitHub CLI uniquement si la commande n'est pas déjà
disponible :

```sh
if ! command -v gh >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install --yes gh
fi
```

Une métrique Coder expose également la version installée avec `gh --version`.

## Vérifications

```sh
terraform init -backend=false -input=false
terraform validate
terraform fmt -check main.tf
cd /home/tmendy/Projects/homelab
./scripts/check-storage-policy.sh
rumdl check --fix docs/activity_report/2026-08-18-install-gh-cli-t3-workspace/2026-08-18-install-gh-cli-t3-workspace.md
```

Résultats :

```text
Success! The configuration is valid.
storage policy ok
Success: No issues found in 1 file
```

## Résultat final

Au prochain démarrage du workspace T3, `gh` sera installé dans l'image du
workspace s'il n'est pas déjà présent.
