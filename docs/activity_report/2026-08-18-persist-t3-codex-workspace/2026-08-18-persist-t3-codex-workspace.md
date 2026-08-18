# Persistance du workspace T3/Codex

## Problème

Le workspace Coder T3 devait conserver les configurations de T3 et Codex,
ainsi que les authentifications déjà effectuées, après un redémarrage de la
machine ou du workspace.

## Raisonnement et commandes

Le template Hermes sert de référence pour la persistance. Inspection des deux
templates :

```sh
sed -n '1,260p' kubernetes/coder/workspace-templates/t3code/main.tf
sed -n '1,300p' kubernetes/coder/workspace-templates/hermes-personal/main.tf
```

Le template T3 avait déjà un PVC dédié :

```hcl
storage_class_name = "nfs-k8s"
resources {
  requests = { storage = "10Gi" }
}
```

Ce PVC est monté sur `/home/coder`, qui est le `$HOME` du conteneur. Les
répertoires `~/.codex`, `~/.config/t3`, `~/.ssh` et `~/project` sont donc déjà
sur le stockage NFS et survivent au remplacement du Pod et au redémarrage d'un
worker.

Le seul état encore éphémère était l'installation globale des paquets npm.
Elle a été déplacée vers `$HOME/.local`, puis rendue conditionnelle :

```sh
export npm_config_prefix="$HOME/.local"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v t3 >/dev/null 2>&1 || ! command -v codex >/dev/null 2>&1; then
  npm install --global t3@latest @openai/codex
fi
```

T3 tentait aussi d'activer `systemd linger` pour démarrer son serveur en
arrière-plan. Cette fonctionnalité n'est pas disponible dans le Pod Kubernetes
du workspace. Le startup script lance donc directement `t3 serve`, conserve son
PID et écrit ses logs dans le PVC :

```sh
server_pid="$HOME/.local/share/t3/serve.pid"
if [ ! -f "$server_pid" ] || ! kill -0 "$(cat "$server_pid")" 2>/dev/null; then
  nohup t3 serve >"$HOME/.local/share/t3/serve.log" 2>&1 &
  echo $! >"$server_pid"
fi
```

## Vérifications

La première validation Terraform a échoué car les providers n'étaient pas
encore présents localement :

```sh
terraform validate
```

Résultat :

```text
Error: missing or corrupted provider plugins
there is no package for coder/coder 2.18.0 cached in .terraform/providers
there is no package for hashicorp/kubernetes 3.2.1 cached in .terraform/providers
```

Après initialisation locale des providers :

```sh
terraform init -backend=false -input=false
terraform validate
```

Résultat :

```text
Terraform has been successfully initialized!
Success! The configuration is valid.
```

```sh
terraform fmt -check kubernetes/coder/workspace-templates/t3code/main.tf
```

Résultat attendu :

```text
(aucune sortie, code retour 0)
```

```sh
./scripts/check-storage-policy.sh
```

Résultat attendu :

```text
storage policy ok
```

## Résultat final

Le PVC existant `nfs-k8s` couvre déjà la configuration T3, la configuration et
l'authentification Codex, les clés SSH et le projet. T3 et Codex sont maintenant
aussi installés dans ce PVC et ne sont installés qu'une seule fois par
workspace. Le serveur T3 démarre automatiquement avec le Pod, sans dépendre de
`systemd linger`.

Après cette modification, republier le template :

```sh
coder templates push t3code \
  --directory kubernetes/coder/workspace-templates/t3code
```
