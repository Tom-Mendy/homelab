# Portfolio summary

## Project

### Homelab Kubernetes platform

Designed and operated a three-node Kubernetes homelab managed with Flux GitOps.
Built local Helm charts for platform and application services, added external
secret delivery with Infisical, moved persistent workloads to shared NFS
storage, and introduced CI checks for secrets, Helm rendering, Kubernetes
schemas, and storage policy violations.

## Technologies

Kubernetes, Flux, Helm, Kustomize, CloudNativePG, Infisical, Authentik,
Traefik, NFS, Grafana, GitHub Actions, Forgejo, Python, Bash.

## What to discuss in an interview

- How GitOps ownership prevents live image updates from conflicting with Git.
- Why worker-local persistent storage was replaced with NFS-backed PVCs.
- How OIDC clients and runtime credentials are kept outside Git.
- How incident reports turned operational failures into repeatable runbooks.
- Which risks remain accepted in a homelab and what evidence is still missing.

## CV version

> Built and operated a three-node Kubernetes homelab with Flux GitOps, Helm,
> Infisical, Authentik, CloudNativePG, and shared NFS storage. Added CI gates
> for secret scanning, manifest schema validation, chart rendering, and
> storage resilience, and documented recovery procedures from real incidents.
