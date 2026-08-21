# Pangolin migration from Hstgr to OVH

## Problem

The Hstgr subscription expires on 27 August 2026. Pangolin had to be moved
from `72.61.113.235` to OVH VM `92.222.90.223` while preserving its database,
certificates, public resources, and Kubernetes/Newt integration. OVH
administration SSH had to use port `2222`; public TCP port `22` had to forward
to Forgejo Git SSH.

## Investigation and backup

The SSH aliases were not usable from the execution environment, so the
provided IP addresses were used directly with `ssh -F /dev/null`.

```text
Hstgr: Ubuntu 24.04.4, Docker 29.7.2, root@72.61.113.235
OVH: Debian 13, Docker initially absent, debian@92.222.90.223
Pangolin Compose: /root/pangolin
Persistent data: /root/pangolin/config, including db/db.sqlite and letsencrypt/acme.json
```

The stopped Hstgr stack was archived before migration:

```text
/root/pangolin-migration-20260821.tgz
SHA256 3bababc2ebef8fc1271813020730977c867eeac9414bf673672517631392afe3
```

The working Hstgr container images were committed and exported to avoid a
moving `latest` tag:

```text
/root/pangolin-images-committed-20260821.tar.gz
SHA256 80cd266f37b12ae8a34100fcb57fd13d1c13668f9488e49bee04c9c6f648c66b
```

## OVH preparation and restore

Docker, Compose, UFW, and the SSH configuration were prepared on OVH. The
first Compose attempt failed because Docker could not allocate the historical
IPv6 pool:

```text
failed to create network pangolin: could not find an available,
non-overlapping IPv6 address pool among the defaults
```

The Compose network was changed to explicit IPv4/IPv6 subnets. A first run
with a newer `latest` image also failed with an SQLite schema mismatch:

```text
SqliteError: no such column: resources.http
```

The incompatible configuration was retained at
`/root/pangolin/config.ovh-incompatible-20260821`; the original configuration
was restored from the archive and the committed Hstgr images were loaded.
Pangolin then reported:

```text
Starting migrations from version 1.18.4
All migrations completed successfully
Dashboard API server is running on http://localhost:3000
Internal API server is running on http://localhost:3001
```

The OVH stack is running with Pangolin healthy, Gerbil running, and Traefik
running. SSH syntax was checked with `sshd -t`, SSH was reloaded, and
`ssh -p 2222 debian@92.222.90.223` succeeded.

## Networking and public resources

UFW allows the required ports:

```text
2222/tcp, 22/tcp, 80/tcp, 443/tcp, 7881/tcp
21820/udp, 51820/udp, 50100:50110/udp
```

Gerbil now publishes TCP `22`, and Traefik has a `tcp-22` entrypoint. Gerbil
also publishes UDP `50100` through `50110`, with matching Traefik UDP
entrypoints. The LiveKit UDP resources target
`matrix-rtc.matrix.svc.cluster.local` on their corresponding ports. Newt
logs confirmed all eleven UDP proxies started, as well as TCP `7881` and
Forgejo TCP `22`.

The Forgejo resource was created through a temporary Newt blueprint because
the Pangolin API had no existing API key:

```yaml
public-resources:
  forgejo-ssh:
    name: Forgejo SSH
    protocol: tcp
    proxy-port: 22
    targets:
      - hostname: forgejo.forgejo.svc.cluster.local
        port: 22
```

The temporary Kubernetes blueprint Pod and ConfigMap were deleted after use.
The permanent Newt deployment has no temporary `hostAliases` override.

Cloudflare record `pangolin.tom-mendy.com` was changed from
`72.61.113.235` to `92.222.90.223`. The other public names are CNAMEs and
therefore followed the change. The repository references in
`kubernetes/matrix/values.yaml` and its README were updated. Blocky was also
updated with the final Pangolin address and successfully reconciled.

## Validation results

Public DNS resolved to `92.222.90.223`.

```text
pangolin.tom-mendy.com  200
authentik.tom-mendy.com 302
forgejo.tom-mendy.com   200
matrix.tom-mendy.com    404 (application route, not a proxy failure)
chat.tom-mendy.com      200
rtc.tom-mendy.com       404 (root route; TCP 7881 target is healthy)
```

The Newt logs reported a successful tunnel and healthy targets for Authentik,
Forgejo, Matrix, Cinny, and LiveKit TCP. Forgejo Git SSH was tested through
the public port 22:

```text
ssh-keyscan -p 22 forgejo.tom-mendy.com
SSH-2.0-OpenSSH_10.2
git ls-remote ssh://git@forgejo.tom-mendy.com:22/Tom-Mendy/homelab.git HEAD
114a0d3fc9e20dd723b725cbbf92c9148ba1d928 HEAD
```

Kubernetes validation showed all listed pods Ready, the Newt pod Ready, and
all Flux HelmReleases `Ready=True`. The storage policy check succeeded:

```text
./scripts/check-storage-policy.sh
storage policy ok
```

Both modified charts rendered successfully with `helm template`. `rumdl
check --fix .` was run; it reported 136 pre-existing Markdown issues in 17
unrelated files and no issue in this report.

## Final state and rollback

The old Hstgr stack was kept available during DNS, Newt, HTTPS, and Forgejo
validation. Its archive, configuration, and image export remain available
for rollback. A rollback consists of restoring the DNS A record to
`72.61.113.235`, retaining Hstgr Compose running, and reverting the repository
IP references if required. The OVH Pangolin data and backups were not removed.
