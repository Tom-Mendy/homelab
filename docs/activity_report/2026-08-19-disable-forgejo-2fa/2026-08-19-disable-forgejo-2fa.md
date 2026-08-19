# Désactivation de la 2FA Forgejo

## Problème

Le compte `Tom-Mendy` ne pouvait plus se connecter à Forgejo. Le passcode
2FA était refusé et l'écran demandait un scratch code.

## Raisonnement et commandes

Le dépôt indique que Forgejo tourne dans Kubernetes. J'ai d'abord vérifié le
déploiement et le stockage avant toute modification :

```text
$ kubectl config current-context
kubernetes-admin@cluster.local

$ kubectl -n forgejo get pods -o wide
NAME                       READY   STATUS    RESTARTS   AGE     IP             NODE
forgejo-7cff569bc5-scd67   1/1     Running   0          2d19h   10.233.71.49   node3
```

Le PVC Forgejo est un PV NFS statique vers `10.0.0.11:/volume1/forgejo`.
Aucune modification de stockage n'était nécessaire.

La première tentative d'administration a échoué, car la commande a été lancée
en root :

```text
$ kubectl -n forgejo exec deploy/forgejo -- forgejo admin user list --admin
Forgejo is not supposed to be run as root. Sorry.
command terminated with exit code 1
```

Le conteneur contient l'utilisateur système `git` avec l'UID `1023`. La même
commande lancée avec cet utilisateur a identifié le compte ciblé :

```text
$ kubectl -n forgejo exec deploy/forgejo -- su -s /bin/sh git -c \
  'forgejo admin user list --admin'
ID   Username  Email             IsActive
1    Tom-Mendy dev@tom-mendy.com true
```

La commande Forgejo disponible pour cette opération est
`forgejo admin user reset-mfa --username`. Je l'ai exécutée pour `Tom-Mendy` :

```text
$ kubectl -n forgejo exec deploy/forgejo -- su -s /bin/sh git -c \
  'forgejo admin user reset-mfa --username Tom-Mendy'
Tom-Mendy's two-factor authentication settings have been removed!
```

## Vérification

Forgejo stocke la configuration 2FA dans la table `two_factor` de sa base
SQLite. Après l'opération, le compte ne possède plus de configuration 2FA :

```text
$ sqlite3 /data/gitea/gitea.db "SELECT u.id,u.lower_name,COUNT(tf.id) \
AS mfa_configs FROM user u LEFT JOIN two_factor tf ON tf.uid=u.id \
WHERE u.id=1 GROUP BY u.id,u.lower_name;"
1|tom-mendy|0
```

## Résultat

La 2FA et les scratch codes du compte `Tom-Mendy` ont été supprimés. La
prochaine connexion ne doit plus demander de passcode 2FA. Le mot de passe
Forgejo reste inchangé.
