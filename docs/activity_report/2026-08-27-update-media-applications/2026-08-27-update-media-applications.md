# Mise à jour des applications média

## Problème

Les images du chart `kubernetes/media` n'étaient plus aux dernières versions
stables publiées. La demande était de mettre à jour Radarr et les applications
associées.

## Raisonnement et commandes

Le chart utilise des images épinglées par digest. J'ai donc interrogé les
registres pour éviter de remplacer ces références par des tags flottants.

```sh
curl -fsSL \
  'https://registry.hub.docker.com/v2/repositories/linuxserver/radarr/tags' \
  | jq -r '.results[] | [.name,.digest,.last_updated] | @tsv'
```

La même vérification a été faite pour qBittorrent, NZBGet, Sonarr, Prowlarr et
Bazarr. Pour Autobrr, la dernière release GitHub et le digest OCI ont été
consultés. Les tags `develop`, `nightly` et `testing` n'ont pas été retenus.

Versions appliquées dans `kubernetes/media/values.yaml` :

| Application | Ancienne version | Nouvelle version |
| --- | --- | --- |
| qBittorrent | 5.2.2 | 5.2.3 |
| NZBGet | 26.1.20260529 | 26.2.20260821 |
| Sonarr | 4.0.17 | 4.0.19 |
| Radarr | 6.1.1 | 6.3.0 |
| Prowlarr | 2.3.5 | 2.5.2 |
| Bazarr | v1.5.6-ls349 | 1.6.0 |
| Autobrr | v1.79.0 | v1.84.0 |

Gluetun, utilisé par NZBGet et qBittorrent, est passé de `v3.41.1` à
`v3.41.3` dans les templates concernés.

## Résultats

Le rendu Helm passe :

```text
helm template exit=0
rendered resources: 43
```

La vérification de stockage passe également :

```text
storage policy ok
storage policy exit=0
```

La recherche des références interdites ne trouve aucune occurrence active de
`local-path` sous `kubernetes/`.

Le contrôle Markdown global a été lancé avec `rumdl check --fix .`. Il remonte
136 problèmes préexistants dans 17 fichiers, principalement des lignes trop
longues, hors des fichiers modifiés par cette activité.

## Résultat final

Les sept applications média et les deux sidecars Gluetun utilisent maintenant
des versions stables récentes, chacune avec son digest. Les PVC et chemins NFS
n'ont pas été modifiés.
