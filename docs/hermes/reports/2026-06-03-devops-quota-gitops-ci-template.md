# Rapport hebdomadaire fin de quota — GitOps CI pour homelab

Date UTC: 2026-06-03T07:24:12Z

## Tâche choisie

Axe aléatoire retenu: **template GitHub Actions pour CI GitOps Kubernetes**.

Objectif: produire un artefact directement réutilisable par Tom pour durcir un dépôt GitOps homelab, sans lire de secrets ni toucher à un système externe.

## Actions réalisées

- Créé un workflow GitHub Actions prêt à adapter pour valider des manifests Kubernetes avant merge.
- Inclus des checks utiles pour un dépôt GitOps homelab:
  - lint des workflows GitHub Actions avec `actionlint`;
  - scan de secrets avec `gitleaks` en mode redaction;
  - lint YAML;
  - rendu des overlays `kustomize`;
  - validation Kubernetes avec `kubeconform`;
  - rendu optionnel de charts Helm si `charts/` existe;
  - permissions GitHub minimales: `contents: read`;
  - concurrency pour annuler les runs obsolètes sur la même ref.
- Vérifié que le fichier YAML créé est syntaxiquement parseable avec Python/PyYAML.
- Vérifié le workflow avec `actionlint v1.7.12` téléchargé temporairement depuis la release publique.
- Aucune lecture de credentials, token, `auth.json`, kubeconfig, talosconfig ou clé API.

## Fichiers créés/modifiés

- Template workflow: `/home/hermes/reports/templates/gitops-manifests-ci.yml`
- Rapport: `/home/hermes/reports/2026-06-03-devops-quota-gitops-ci-template.md`

## Versions publiques consultées

Récupérées via GitHub API publique, sans token:

| Outil | Version repérée | Source |
|---|---:|---|
| Kubernetes | `v1.36.1` | https://github.com/kubernetes/kubernetes/releases/tag/v1.36.1 |
| gitleaks | `v8.30.1` | https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1 |
| kubeconform | `v0.7.0` | https://github.com/yannh/kubeconform/releases/tag/v0.7.0 |
| Helm | `v4.2.0` | https://github.com/helm/helm/releases/tag/v4.2.0 |
| kustomize | `kustomize/v5.8.1` | https://github.com/kubernetes-sigs/kustomize/releases/tag/kustomize/v5.8.1 |
| yamllint | `v1.38.0` | https://github.com/adrienverge/yamllint/releases/tag/v1.38.0 |
| actionlint | `v1.7.12` | https://github.com/rhysd/actionlint/releases/tag/v1.7.12 |
| Trivy | `v0.71.0` | https://github.com/aquasecurity/trivy/releases/tag/v0.71.0 |

Note: `kubectl` n’a pas de release latest exploitable sur `kubernetes/kubectl` via l’endpoint testé; j’ai donc pris la release Kubernetes stable repérée comme référence de version de schémas pour `kubeconform`.

## Comment utiliser le template

1. Copier le fichier vers un dépôt GitOps:

```bash
mkdir -p .github/workflows
cp /home/hermes/reports/templates/gitops-manifests-ci.yml .github/workflows/gitops-manifests-ci.yml
```

2. Adapter si besoin les chemins surveillés:

```yaml
clusters/**
apps/**
charts/**
```

3. Adapter `KUBERNETES_VERSION` à la version réelle du cluster homelab/Talos.

4. Ouvrir une PR et vérifier que la CI échoue volontairement si:
   - un secret non chiffré est committé;
   - un YAML est invalide;
   - un `kustomize build` casse;
   - un manifest ne respecte pas les schémas Kubernetes attendus.

## Points d’attention sécurité

- Le workflow utilise `gitleaks detect --redact`: les résultats doivent masquer les secrets détectés.
- Il ne faut pas injecter de kubeconfig ou talosconfig dans cette CI de validation statique: elle n’a pas besoin d’accès cluster.
- Pour une sécurité supérieure, Tom pourra plus tard pinner les GitHub Actions par SHA au lieu des tags (`actions/checkout@v4`).
- Le template installe des binaires depuis GitHub/get.helm.sh; pour un repo très sensible, ajouter une vérification checksum/signature.
- `kubeconform -ignore-missing-schemas` évite de bloquer sur les CRD; pour un repo mature, ajouter les schemas CRD ou retirer cette option progressivement.

## Prochaines actions utiles pour Tom

1. Tester ce workflow sur un dépôt GitOps non critique ou une branche dédiée.
2. Si Flux ou Argo CD est utilisé, ajouter une étape spécifique:
   - Flux: `flux diff`/validation de manifests générés si le contexte le permet;
   - Argo CD: `argocd app diff` seulement dans une CI avec accès cluster explicitement contrôlé.
3. Ajouter Trivy plus tard pour scanner les images référencées dans les manifests, mais éviter de rendre la CI trop lente dès le début.
4. Compléter avec une règle de protection de branche: PR obligatoire + CI verte obligatoire avant merge.
