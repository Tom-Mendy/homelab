# Corriger le HelmChart PostgreSQL de Forgejo

## Problème

Flux signalait que `flux-system-forgejo-postgres` était en échec avec cette
erreur :

```text
invalid chart reference: stat .../source/kubernetes/forgejo-postgres:
no such file or directory
```

Le chart `kubernetes/forgejo-postgres` avait été fusionné dans
`kubernetes/forgejo`, mais un ancien objet Flux restait dans le cluster.

## Diagnostic

J'ai comparé les ressources du dépôt avec celles du cluster :

```sh
rg -n -i 'forgejo-postgres|postgres.*forgejo|chart:' kubernetes
rg --files kubernetes | rg 'forgejo|postgres'
kubectl get helmrelease -A
kubectl -n flux-system get helmchart
```

Le dépôt ne contient plus `kubernetes/forgejo-postgres`. Il contient
`kubernetes/forgejo`, dont le template crée déjà le Cluster CNPG
`forgejo-postgres`. Dans le cluster, les résultats importants étaient :

```text
flux-system  forgejo  True  UpgradeSucceeded
flux-system  flux-system-forgejo  ...  True
flux-system  flux-system-forgejo-postgres  ./kubernetes/forgejo-postgres  ...  False
```

La ressource `HelmRelease/forgejo-postgres` n'existait pas. Le
`HelmChart/flux-system-forgejo-postgres` était donc orphelin.

Le chart actuel se rend correctement :

```sh
helm template forgejo ./kubernetes/forgejo
```

```text
helm template exit=0
```

## Correction

J'ai supprimé uniquement le HelmChart généré et obsolète :

```sh
kubectl -n flux-system delete helmchart flux-system-forgejo-postgres
```

```text
helmchart.source.toolkit.fluxcd.io "flux-system-forgejo-postgres" deleted
from flux-system namespace
```

J'ai ensuite forcé la réconciliation de la source Git et de la Kustomization :

```sh
flux reconcile kustomization flux-system -n flux-system --with-source
```

```text
fetched revision refs/heads/main@sha1:6a80a9b39963770123026e51ce531e66e0797ac1
applied revision refs/heads/main@sha1:6a80a9b39963770123026e51ce531e66e0797ac1
```

## Résultat

Le HelmChart obsolète ne réapparaît plus. Le seul chart Forgejo est maintenant
`flux-system-forgejo`, qui pointe vers `./kubernetes/forgejo` et est prêt.

```text
flux-system-forgejo  ./kubernetes/forgejo  True
True UpgradeSucceeded Helm upgrade succeeded for release forgejo/forgejo.v77
```

Le Cluster `forgejo-postgres` reste géré par le chart Forgejo actuel. Aucune
donnée PostgreSQL ni aucun PVC n'a été supprimé.
