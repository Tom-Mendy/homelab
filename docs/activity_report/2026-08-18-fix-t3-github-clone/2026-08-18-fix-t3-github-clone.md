# Correction du clonage GitHub dans le workspace T3

## Problème

Le clonage depuis le lien GitHub de T3 Code échouait avec :

```text
Source control repository operation cloneRepository failed for unknown:
Destination path already exists and is not empty.
```

## Cause

Le startup script du template créait `~/project` et y clonait automatiquement le
dépôt Forgejo `homelab`. T3 Code utilisait ensuite cette même destination pour
le dépôt choisi via son lien GitHub.

## Correction

Le clonage automatique Forgejo et la création préalable de `~/project` ont été
supprimés du template T3. Le workspace installe toujours T3, Codex, GitHub CLI
et démarre `t3 serve`, mais T3 Code est maintenant seul responsable du clonage.

## Vérifications

```sh
terraform init -backend=false -input=false
terraform validate
terraform fmt -check main.tf
cd /home/tmendy/Projects/homelab
./scripts/check-storage-policy.sh
rumdl check --fix docs/activity_report/2026-08-18-fix-t3-github-clone/2026-08-18-fix-t3-github-clone.md
git diff --check
```

Résultats :

```text
Success! The configuration is valid.
storage policy ok
Success: No issues found in 1 file
```

## Résultat final

Après publication du template et redémarrage du workspace, le lien GitHub de T3
Code pourra cloner dans une destination vierge.
