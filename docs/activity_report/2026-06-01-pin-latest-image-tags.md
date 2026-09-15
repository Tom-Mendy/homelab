# Pin Latest Image Tags

## Problem

Many workloads used `latest` image tags. A pod restart could pull different
image content without a Git change.

## Reasoning

For each public image, remote registry tags were checked with `crane`. The
chosen rule was:

1. Prefer an Alpine variant when upstream publishes one.
2. Otherwise prefer a slim/minimal variant when upstream publishes one.
3. Otherwise use the newest stable exact version tag.
4. Always append the registry digest.

`crane` was installed to `/tmp` only:

```sh
GOBIN=/tmp go install github.com/google/go-containerregistry/cmd/crane@v0.20.6
```

Example digest lookup:

```sh
/tmp/crane digest vaultwarden/server:1.36.0-alpine
```

SearXNG only publishes `latest`, so it was pinned by digest only:

```text
searxng/searxng@sha256:35b089054ac9b4257976107e71673d9e30ac17c9b50bbf8b4783f2f6d1d1981f
```

Endfield uses the private Forgejo registry. Even with the Kubernetes pull
secret, the registry token endpoint returned HTTP 503, so no digest could be
researched safely:

```text
GET https://forgejo.tom-mendy.com/v2/token ... 503 Service Unavailable
```

## Changes

Pinned these image references:

```text
vaultwarden/server:1.36.0-alpine@sha256:d3531610b486905943706b235e97159331801c6856e1367a93a5905e2b40f204
deluan/navidrome:0.61.2@sha256:9fa40b3d8dec43ceb2213d1fa551da3dcfef6ac6d19c2e534efb92527c2bafd2
spx01/blocky:v0.30.0@sha256:d9f15eddffedded40797406349012cbd5966ef99c286b13321e7a76efddb9bdc
qmcgaw/gluetun:v3.41.1@sha256:1a5bf4b4820a879cdf8d93d7ef0d2d963af56670c9ebff8981860b6804ebc8ab
ollama/ollama:0.9.6@sha256:f478761c18fea69b1624e095bce0f8aab06825d09ccabcd0f88828db0df185ce
ghcr.io/gethomepage/homepage:v1.13.1@sha256:d8d784e5090111b6e4c56dfd90e272d2953a2094e87349f647165df0fa6c4401
ghcr.io/atuinsh/atuin:18.16.1@sha256:9d4d79507b51be6d292b218f5cc791d79ca0a72f51ab48f786b091bd6eafb39f
ghcr.io/autobrr/autobrr:v1.79.0@sha256:5b8c29a86598907496af01ec75ef21f9c0e4e28ce9d6ae6496ef91c71543ec20
stirlingtools/stirling-pdf:2.9.2@sha256:3fcfa4d6b6ff22fdbf96ff2aae98dc2fb6d8c1ba0afab1dd2fdfdcdc9ab543c4
ghcr.io/actions/actions-runner:2.334.0@sha256:b6614fce332517f74d0a76e7c762fb08e4f2ff13dcf333183397c8a5725b6e8e
lscr.io/linuxserver/qbittorrent:5.2.1@sha256:715d2bfbcf1cd3d734cbbd4fbd599eb7ea0642eaa079a372dd0d343f59516700
lscr.io/linuxserver/nzbget:26.1.20260529@sha256:1fd6f36c5856d7e3d7d3f792912d805e123dc0003e028edda4f3f7405d7bc80b
lscr.io/linuxserver/sonarr:4.0.17@sha256:0b5c4803f92456fb9b65bae8375716ea120b4ea17b3cced7da32b63f0085782b
lscr.io/linuxserver/radarr:6.1.1@sha256:079e48870584baf2a3e7e43e7ba6d3c834555931851a59c82c51cc792d285caf
lscr.io/linuxserver/prowlarr:2.3.5@sha256:c9fe528f34b1fd3715438b6f6d6991d64e2965f2c055db36398bc66a0e7eab01
lscr.io/linuxserver/bazarr:v1.5.6-ls349@sha256:95f27692c3de6dbe130cd035d342d8138ec74ade7b62cfc52e11ae222c52c855
ghcr.io/muety/wakapi:2.17.4@sha256:6fce764acf8775e1166e8b03e59fb6b34744e4a9fba5e98d9ea15d341db31bf8
fosrl/newt:1.12.5@sha256:3c009663332145cae39b940b07857469038d5e9d71aacb1497e78795ba4e3b9b
zadam/trilium:0.63.7@sha256:a0b5a6a5fd7a64391ae6039bbcd5493151a77a1d5470ef5911923c64d0c232c0
```

## Validation

Remaining `latest` values:

```text
kubernetes/endfield/values.yaml:5: tag: latest
```

This is expected until the private registry digest can be queried or CI
publishes immutable tags.

Render checks:

```text
./kubernetes/test-helm-chart.sh
OK for all tested charts

helm template newt ... -f kubernetes/newt/newt-values.yaml
image: docker.io/fosrl/newt:1.12.5@sha256:3c009663...

helm template gha-runner-scale-set ... -f runner-scale-set-*-values.yaml
image: ghcr.io/actions/actions-runner:2.334.0@sha256:b6614fce...
```

Server dry-run accepted renderable changed resources:

```text
kubectl apply --dry-run=server -f /tmp/homelab-image-pin-render.yaml
deployment.apps/atuin configured (server dry run)
deployment.apps/blocky configured (server dry run)
deployment.apps/homepage configured (server dry run)
deployment.apps/navidrome configured (server dry run)
deployment.apps/vaultwarden configured (server dry run)
deployment.apps/stirling-pdf configured (server dry run)
deployment.apps/searxng configured (server dry run)
deployment.apps/ollama configured (server dry run)
deployment.apps/trilium configured (server dry run)
```

Storage policy:

```text
storage policy ok
```

## Outcome

All public `latest` image references were pinned to exact tags and digests. The
only remaining `latest` is the private Endfield image, blocked by Forgejo
registry HTTP 503.
