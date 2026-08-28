# Public publication procedure

This repository is published as a direct mirror of the operational Forgejo
repository. The live domains, network values, Helm charts, scripts, and Flux
resources are intentionally preserved.

## Before publishing

Check the working tree and scan the full history:

```bash
git status --short
gitleaks git --redact --verbose
```

Do not publish credentials, tokens, private keys, kubeconfig files, or rendered
runtime secrets. Public service endpoints may remain when they are intentional,
reachable, and protected by their normal authentication controls.

## Files removed from the public tree

The repository no longer tracks the personal activity journal, temporary
backlogs, Hermes planning material, or the network migration scratchpad. Keep
those materials outside the public repository if they are still useful for
private learning.

## Validation

Run the same checks used by Forgejo Actions:

```bash
./scripts/check-storage-policy.sh
./scripts/test-helm-chart.sh
./scripts/render-local-charts-for-kubeconform.sh
kubeconform -strict -summary -ignore-missing-schemas .forgejo-rendered
rumdl check --fix .
```

The mirror should contain the resulting working tree and the same commit history
as the Forgejo repository. This cleanup does not rewrite older commits, so files
removed from the current tree remain available in historical revisions.
