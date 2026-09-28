# Security

This repository does not contain production secrets.

Secrets are managed outside Git using Infisical and Kubernetes secrets are
generated at deployment time.

The public service domains and network values describe the live homelab and are
intentional. They are not access credentials. Protecting the services still
depends on authentication, authorization, network controls, and regular
updates.

The repository is scanned with:

- Gitleaks
- Kubernetes schema validation
- Helm lint
- YAML linting

Please do not report public endpoint visibility as a secret exposure. Report
credentials, tokens, private keys, or other access material privately.

If you find sensitive information, please contact me privately.
