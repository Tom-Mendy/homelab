# Harbor proxy cache

Harbor provides public proxy-cache projects for the upstream registries used by
the cluster. The projects are intentionally read-only and public: they contain
only artifacts fetched from public upstream registries, and this allows
containerd to pull without distributing Harbor credentials to every namespace.

## Upstream credentials

Create these read-only secrets in Infisical under `/harbor/proxy`:

- `DOCKERHUB_USERNAME` and `DOCKERHUB_PASSWORD`
- `GHCR_USERNAME` and `GHCR_PASSWORD` (`read:packages` only)
- `QUAY_USERNAME` and `QUAY_PASSWORD` (robot account, pull only)

Never commit these values. The Harbor configuration job accepts missing values
and uses anonymous upstream access, but authenticated access is recommended to
avoid upstream rate limits.

## Transparent node cache

Kubernetes keeps using normal references such as `docker.io/library/alpine`.
Run `scripts/configure-containerd-harbor-mirror.sh` as root on each node. The
script writes `/etc/containerd/certs.d/<registry>/hosts.toml`, keeps a backup,
and restarts containerd. Apply it one node at a time; cordon and drain workers
before restarting them. To roll back, restore the newest `.harbor-backup.*`
file for each registry and restart containerd.

The mirror covers Docker Hub, GHCR, Quay, `registry.k8s.io`, `lscr.io`, and
`nvcr.io`. Docker or Podman clients outside the cluster must use the explicit
Harbor project prefix, for example:

```text
harbor.home.tom-mendy.com/proxy-dockerhub/library/alpine:latest
```

## Security and lifecycle

Proxy projects automatically scan artifacts with Trivy, generate SPDX SBOMs,
and prevent pulls at `high` severity or above. Harbor's default seven-day
proxy retention and per-project quotas limit unbounded growth. Keep workload
references pinned by digest whenever possible.

Harbor supports Cosign and Notation verification, but signature enforcement is
not enabled on public proxy projects because upstream signatures are not
uniform. Use signature enforcement for private first-party projects.
