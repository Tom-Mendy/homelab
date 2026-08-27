# Public publication procedure

The live repository contains environment-specific values used by the homelab.
Publish a sanitized export instead of copying the live working tree directly.

## Create the export

Run this command from the repository root and choose a new output directory
outside the repository:

```bash
uv run python scripts/export-public-repo.py /tmp/homelab-public
```

The exporter removes private Forgejo workflows, backlogs, detailed activity
reports, internal Hermes reports, network migration notes, and cluster access
instructions. It replaces private hostnames, addresses, registry endpoints,
and storage paths with documentation values.

The exporter refuses to overwrite an existing directory and fails if known
private identifiers remain in the result.

## Audit the history

The exporter handles the current tree only. Before publishing history, create a
recoverable backup and run a full-history secret scan:

```bash
git bundle create /tmp/homelab-private-backup.bundle --all
gitleaks git --redact --verbose
```

If the audit finds a secret or a private identifier that was removed from the
public tree, rewrite the public clone with `git-filter-repo`. Keep the original
bundle private and never force-push rewritten history to the live operational
repository without a separate maintenance decision.

## Final checks

From the exported directory:

```bash
git diff --check
./scripts/check-storage-policy.sh
./scripts/test-helm-chart.sh
./scripts/render-local-charts-for-kubeconform.sh
rumdl check README.md CONTRIBUTING.md SECURITY.md \
  docs/architecture.md docs/portfolio-summary.md docs/publication.md
```

Run `gitleaks dir` against the exported repository and inspect the file list
before creating the GitHub repository. Do not copy `.env` files, kubeconfig files,
tokens, private keys, rendered runtime secrets, or cluster credentials.
