# Security

This repository does not contain production secrets.

Secrets are managed outside Git using Infisical and Kubernetes secrets are
generated at deployment time.

The repository is scanned with:

- Gitleaks
- Kubernetes schema validation
- Helm lint
- YAML linting

If you find sensitive information, please contact me privately.
