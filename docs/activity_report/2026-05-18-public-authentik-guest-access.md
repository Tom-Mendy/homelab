# Public authentik and guest access checklist

## Problem

Expose authentik at `authentik.tom-mendy.com` through Pangolin, then use
manual guest invitations for Forgejo and selected apps.

The URLs and ingress example below follow the current hostname policy.
Use the canonical hostname for all authentik access and DNS mappings.

Infisical must remain private, and real secrets must not be committed to Git.

## Reasoning path

The repo uses `*.home.tom-mendy.com` for private services and Traefik ingress
inside the cluster. Pangolin/Newt already exists for public tunnel access.

The authentik Kubernetes ingress must use `authentik.tom-mendy.com`.
Pangolin can reach authentik directly through Kubernetes DNS because its
connector runs inside the cluster. The official authentik chart renders the
server Service as:

```text
http://authentik-server.authentik.svc.cluster.local:80
```

Guest onboarding should use manual authentik invitations instead of open public
registration. This keeps Forgejo and later applications controlled by group
membership.

## Commands to run

Render the local authentik helper chart:

```sh
helm template test kubernetes/authentik
```

Render all local charts:

```sh
./kubernetes/test-helm-chart.sh
```

Check storage policy:

```sh
./scripts/check-storage-policy.sh
```

Check Markdown:

```sh
rumdl check --fix .
```

After pushing, verify Argo CD:

```sh
kubectl get applications -n argocd authentik
kubectl get ingress -n authentik authentik-server
kubectl get svc -n authentik authentik-server
```

Manual browser checks:

```text
https://authentik.tom-mendy.com
```

## Command results

Local authentik chart render succeeded:

```text
helm template test kubernetes/authentik
```

Official authentik chart render confirmed the internal Service name and port:

```text
kind: Service
metadata:
  name: authentik-server
spec:
  ports:
    - name: http
      port: 80
      targetPort: 9000
```

The Kubernetes Ingress example uses the canonical hostname:

```text
kind: Ingress
metadata:
  name: authentik-server
spec:
  rules:
    - host: "authentik.tom-mendy.com"
```

All local chart renders succeeded:

```text
=== blocky ===
OK
=== homepage ===
OK
=== traefik ===
OK
=== keel ===
OK
=== prometheus ===
OK
=== grafana ===
OK
=== navidrome ===
OK
=== vaultwarden ===
OK
=== forgejo ===
OK
=== forgejo-runner ===
OK
=== searxng ===
OK
=== endfield ===
OK
=== infisical-postgres ===
OK
=== authentik-postgres ===
OK
=== authentik ===
OK
```

Storage policy succeeded:

```text
storage policy ok
```

Markdown validation succeeded:

```text
Success: No issues found in 26 files
```

## Final outcome

The repository now includes:

- authentik ingress configuration uses `authentik.tom-mendy.com`.
- A manual checklist at `docs/authentik-infisical-guest-checklist.md` for
  Infisical, authentik, Pangolin, guest groups, invitations, and Forgejo SSO.
  Pangolin should route the public `authentik.tom-mendy.com` hostname to
  `http://authentik-server.authentik.svc.cluster.local:80`.

The remaining work is intentionally manual in Infisical, authentik, Pangolin,
public DNS, and Forgejo.
