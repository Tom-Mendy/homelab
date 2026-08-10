# Prepare the qBittorrent NymVPN Pilot

## Problem

The media chart routed qBittorrent and NZBGet through ProtonVPN Gluetun
sidecars. The goal was to stop paying for a dedicated ProtonVPN subscription
and reuse the existing NymVPN subscription without putting credentials in Git
or placing VPN state on a worker-local disk.

NymVPN does not expose a static WireGuard configuration that Gluetun can use.
The supported Linux client consists of `nym-vpnd` and `nym-vpnc`, so the pilot
needed a dedicated sidecar image and persistent Nym device state.

## Reasoning and Commands

The repository search showed that qBittorrent and NZBGet used the media chart's
ProtonVPN configuration. SearXNG has a separate Gluetun sidecar and is
intentionally left for the final migration.

```sh
rg -n -i 'proton|gluetun|qbittorrent|vpn' kubernetes
```

The official NymVPN release API identified version `2026.10.0` and the package
digests used by the Dockerfile:

```text
nym-vpnc_2026.10.0_amd64.deb  sha256:fd7c0ab9b638ffc15300697e5af8efcb4afc1ed3d8010b7523370fa90969cd3d
nym-vpnd_2026.10.0_amd64.deb  sha256:408f948922e64596c9ae4c727de6e8b8c568756937dd4271c69dd9df41161afc
```

The image was built locally:

```sh
docker build --pull --tag nymvpn-sidecar:test kubernetes/media/nymvpn
```

Result:

```text
Successfully tagged localhost/nymvpn-sidecar:test
```

The installed CLI confirmed the commands used by the entrypoint:

```sh
docker run --rm --entrypoint nym-vpnc nymvpn-sidecar:test connect --help
docker run --rm --entrypoint nym-vpnc nymvpn-sidecar:test tunnel set --help
docker run --rm --entrypoint nym-vpnc nymvpn-sidecar:test gateway set --help
```

The output confirmed `connect --wait`, two-hop and IPv6 switches, and country
selectors for entry and exit gateways.

An initial RPC test failed with:

```text
Authentication is required to access the daemon
```

`nym-vpnd run-as-service --disable-client-verification` fixed the RPC access.
This is contained to the sidecar because `/var/run/nym-vpn.sock` is not shared
with qBittorrent. The same test also showed that `account get` exits with zero
for `Account state: LoggedOut`, so the entrypoint detects the persisted
`access_code.json` or `mnemonic.json` files instead.

A short daemon test without an account verified startup and DNS bootstrap:

```sh
timeout 12 docker run --rm --dns=127.0.0.1 \
  --cap-add NET_ADMIN --device /dev/net/tun \
  --entrypoint nym-vpnd nymvpn-sidecar:test
```

Useful output included:

```text
Starting socket listener on: /var/run/nym-vpn.sock
Running DNS resolver on 127.0.0.1:53 (udp, tcp)
Updated topology
```

The initial daemon run also logged missing cache files under `/etc/nym`. This
was expected on first boot; the daemon then created its default configuration.
It logged that split tunneling could not initialize in the test container, but
split tunneling is disabled and is not part of the Kubernetes design.

The live cluster check failed before any deployment was attempted:

```sh
kubectl get nodes -o wide
```

Result:

```text
The connection to the server 10.0.0.21:6443 was refused
```

This failure prevented secret reconciliation, image pulling, rollout and leak
tests. No live Kubernetes resource was modified.

The API server became reachable later in the activity. A second inspection
showed `node1` and `node2` ready but `node3` unreachable since August 3. The
Infisical PostgreSQL and Redis pods were still terminating on `node3`, while
replacement Infisical application pods on `node2` failed because PostgreSQL
was unavailable:

```text
connect ECONNREFUSED 10.233.37.35:5432
```

The media `InfisicalStaticSecret` consequently reported
`InfisicalConnection is not ready`. A key-name-only Secret audit found an
existing Forgejo pull secret in the Endfield namespace, but no
`NYM_ACCESS_CODE` anywhere in the cluster. No Secret value was read or printed.
The pilot was therefore not applied: doing so would only place qBittorrent in
`ImagePullBackOff` or block it at its VPN startup probe.

Repository validation completed with:

```sh
./scripts/test-helm-chart.sh
./scripts/check-storage-policy.sh
docker run --rm --volume "$PWD/.forgejo-rendered:/manifests:ro" \
  ghcr.io/yannh/kubeconform:master \
  -strict -summary -ignore-missing-schemas /manifests
rumdl check --fix .
```

The Helm script reported `OK` for all active local charts, the storage script
reported `storage policy ok`, and kubeconform returned:

```text
Summary: 152 resources found in 23 files - Valid: 125, Invalid: 0,
Errors: 0, Skipped: 27
```

The system did not have a local `kubeconform` executable, so the first direct
attempt failed with `command not found`. Running the same official container
used by Forgejo Actions completed successfully.

## Forgejo automatic token test

Before creating a persistent registry secret, commit `1d3187d` changed the
publication workflow to authenticate with the short-lived token created for
each Forgejo Actions run:

```yaml
env:
  REGISTRY_USERNAME: ${{ forgejo.repository_owner }}
  FORGEJO_TOKEN: ${{ secrets.FORGEJO_TOKEN }}
```

The run was initially queued because the Forgejo runner had not accepted a
task since August 3. Its pod was healthy and registered with the required
`ubuntu-latest` label, but had a stale session. A controlled deployment restart
restored polling:

```console
$ kubectl rollout restart deployment/forgejo-runner-homelab \
    --namespace forgejo-runner
deployment.apps/forgejo-runner-homelab restarted
deployment "forgejo-runner-homelab" successfully rolled out
```

The runner then processed the test. `docker login` completed successfully, but
the actual push failed. Forgejo's registry log showed that authentication and
token issuance worked:

```text
GET /v2/token?account=Tom-Mendy&... 200 OK
GET /v2/ 200 OK
GET /v2/token?...repository:tom-mendy/nymvpn-sidecar:pull,push... 200 OK
```

Blob uploads were nevertheless rejected because the automatic repository token
does not grant package-owner write access:

```text
POST /v2/tom-mendy/nymvpn-sidecar/blobs/uploads/ 401 Unauthorized
```

The `Log in to Forgejo registry` step succeeded, while `Build and push image`
failed. This live test confirms that `FORGEJO_TOKEN` cannot replace a
package-write token for this Forgejo 15.0.2 instance. No registry credential
was created during the test.

## Package token publication and anonymous pull

The repository-level `REGISTRY_TOKEN` secret was then added with package write
permission. The username remained non-secret and came from
`forgejo.repository_owner`. Commit `aa730d7` triggered a second publication.
All three steps succeeded:

```text
Checkout                    success
Log in to Forgejo registry  success
Build and push image        success
```

Forgejo stored tag `2026.10.0-1` with an AMD64 image manifest digest of
`sha256:3934938c713e780ead211a74d1a64560aa02494768dca53938a591eaa6058880`.
The registry was slow because package data is on shared storage: individual
blob uploads took up to about three minutes and the runner reported temporary
`UpdateLog` and `UpdateTask` deadline warnings. The uploads continued and the
run completed successfully.

A disposable pod on `node3` then pulled and ran the image without an
`imagePullSecret`:

```console
$ kubectl run nymvpn-image-pull-test --namespace media \
    --image=forgejo.tom-mendy.com/tom-mendy/nymvpn-sidecar:2026.10.0-1 \
    --image-pull-policy=Always --restart=Never --command -- /bin/true
pod/nymvpn-image-pull-test condition met
Succeeded imageID=forgejo.tom-mendy.com/tom-mendy/nymvpn-sidecar@sha256:68b13bf...
```

The pod was deleted after the test. Because anonymous pulls work, the media
chart does not create a long-lived registry credential. Only the CI write token
is required.

## GitOps rollout

The first Argo CD attempt exposed a pre-existing diff on dynamically bound PVCs:

```text
PersistentVolumeClaim "qbittorrent-config-pvc" is invalid:
spec: Forbidden: spec is immutable after creation
- "VolumeName": "pvc-6f588b16-79b2-437b-8c90-8bcf180e93e4"
+ "VolumeName": ""
```

The same error affected the other media configuration PVCs. No PVC was deleted
or recreated. The media Application was changed to ignore only
`/spec/volumeName`, which Kubernetes assigns after binding, and to use
`RespectIgnoreDifferences=true`. The stale retry operation had captured the old
options and first had to finish; a new explicit sync then succeeded:

```text
Synced Healthy Succeeded
```

Both qBittorrent PVCs use shared NFS storage:

```text
qbittorrent-config-pvc   Bound   5Gi   nfs-k8s
qbittorrent-nymvpn-pvc   Bound   1Gi   nfs-k8s
```

Infisical synchronized `NYM_ACCESS_CODE` into `nymvpn-credentials` without its
value being read or printed. Nym accepted the account, selected the requested
two-hop route and connected before Kubernetes started qBittorrent.

## Network validation

The qBittorrent container shares the pod network namespace with NymVPN. Its
observed public address differed from the execution host and its reported exit
country was Switzerland:

```text
egress_isolated=yes
vpn_country=CH
```

DNS resolution from the qBittorrent container also succeeded through the Nym
resolver. For the kill-switch test, the tunnel was disconnected with
`nym-vpnc disconnect --wait`. An immediate HTTPS request failed before DNS
could return an address:

```text
curl: (6) Could not resolve host: api.ipify.org
kill_switch_blocked=yes
```

The tunnel was explicitly reconnected and returned `State: Connected`. A
1 MiB HTTPS download from the qBittorrent network namespace then succeeded:

```text
download_test_bytes=1048576
vpn_country=CH
```

## Final Outcome

Forgejo now uses `forgejo.tom-mendy.com` consistently as its canonical web and
OCI registry domain. The former `.home` name remains only as a temporary local
DNS alias.

The unauthenticated registry probe returned the expected authentication
challenge:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://forgejo.tom-mendy.com/v2/
```

```text
401
```

The NymVPN 2026.10.0 image is published by Forgejo Actions using one scoped CI
secret, while Kubernetes pulls it without registry credentials. qBittorrent is
running with the native NymVPN sidecar, starts only after the tunnel is ready,
uses NymVPN DNS, reads its access code from Infisical and persists VPN state on
an `nfs-k8s` PVC.

The live rollout, egress isolation, Swiss exit, DNS, kill-switch and download
checks passed. Argo CD is `Synced`, `Healthy`, and `Succeeded`. NZBGet and
SearXNG remain on ProtonVPN during the 48-hour qBittorrent pilot; no BitTorrent
payload was added automatically for a seeding test.
