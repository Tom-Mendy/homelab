# Fix Forgejo Actions Runner Routing

## Problem

Forgejo Actions showed `storage-policy.yml` runs for recent pushes, but the
runs finished in `0s` and opening a run returned a Forgejo `404` page.

The repository had mixed Forgejo hostnames after the Forgejo 15 and root URL
change:

- Forgejo `ROOT_URL` rendered as `https://forgejo.tom-mendy.com/`.
- The Kubernetes ingress still served `forgejo.home.tom-mendy.com`.
- The Forgejo runner connected to `https://forgejo.home.tom-mendy.com/`.
- Homepage linked users to `https://forgejo.home.tom-mendy.com/`.

The desired canonical user-facing URL is `https://forgejo.tom-mendy.com/`.
Public access is expected to be routed through Pangolin/Newt to the in-cluster
Forgejo service, while the `.home` ingress remains available as a private
recovery route.

## Reasoning path

Search the repository for Forgejo Actions, runner, and hostname configuration:

```sh
rg -n "forgejo|runner|actions|storage-policy|root_url|ROOT_URL" -S .
```

Render the Forgejo chart:

```sh
helm template test kubernetes/forgejo
```

Relevant rendered output before the fix:

```yaml
- name: FORGEJO__server__ROOT_URL
  value: "https://forgejo.tom-mendy.com/"
```

The same rendered chart showed the private ingress host:

```yaml
rules:
  - host: forgejo.home.tom-mendy.com
```

Render the Forgejo runner chart:

```sh
helm template test kubernetes/forgejo-runner
```

Relevant rendered output before the fix:

```yaml
server:
  connections:
    forgejo:
      url: "https://forgejo.home.tom-mendy.com/"
```

Because the runner runs inside the cluster, it does not need to use either the
public hostname or the private ingress hostname. Using the Kubernetes service
URL avoids mixed external routing and TLS behavior for runner callbacks:

```yaml
forgejo:
  url: http://forgejo.forgejo.svc.cluster.local:3000/
```

Update the user-facing homepage link to the canonical public Forgejo URL:

```yaml
href: https://forgejo.tom-mendy.com/
```

Live cluster inspection was attempted with read-only `kubectl` commands, but
the sandbox blocked access to the Kubernetes API:

```text
Unable to connect to the server:
dial tcp 192.168.1.11:6443: socket: operation not permitted
```

## Command results

Render the Forgejo chart after the change:

```sh
helm template test kubernetes/forgejo
```

Relevant output:

```yaml
- name: FORGEJO__server__ROOT_URL
  value: "https://forgejo.tom-mendy.com/"
```

Render the Forgejo runner chart after the change:

```sh
helm template test kubernetes/forgejo-runner
```

Relevant output:

```yaml
server:
  connections:
    forgejo:
      url: "http://forgejo.forgejo.svc.cluster.local:3000/"
```

Check all local Helm charts:

```sh
./kubernetes/test-helm-chart.sh
```

Output:

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

Check the repository storage policy:

```sh
./scripts/check-storage-policy.sh
```

Output:

```text
storage policy ok
```

Confirm no active Kubernetes YAML uses `local-path`:

```sh
rg -n "local-path" kubernetes --glob '*.yaml' --glob '*.yml'
```

Output:

```text
```

## Final outcome

The runner now connects to Forgejo through the in-cluster Kubernetes service.
Forgejo keeps the public canonical `ROOT_URL`, and Homepage now links to the
same public URL.

No storage changes were made. The Forgejo data volume remains the existing
static Synology NFS-backed PV, and the runner continues to use ephemeral
`emptyDir` storage for runner work and Docker state.

After Argo CD applies the change, verify that `forgejo.tom-mendy.com` is routed
in Pangolin to `http://forgejo.forgejo.svc.cluster.local:3000`, then rerun or
push a test commit for `.forgejo/workflows/storage-policy.yml`.
