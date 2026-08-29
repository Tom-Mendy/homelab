# syntax=docker/dockerfile:1.7

FROM --platform=$BUILDPLATFORM golang:1.26.6-alpine AS buildkit
ARG BUILDKIT_VERSION=v0.33.0-rc1
ARG CNI_VERSION=v1.9.1
ARG ROOTLESSKIT_VERSION=v3.0.1
RUN apk add --no-cache git make
WORKDIR /src
RUN git clone --depth 1 --branch "${BUILDKIT_VERSION}" https://github.com/moby/buildkit.git buildkit \
    && git clone --depth 1 --branch "${CNI_VERSION}" https://github.com/containernetworking/plugins.git cni \
    && git clone --depth 1 --branch "${ROOTLESSKIT_VERSION}" https://github.com/rootless-containers/rootlesskit.git rootlesskit
RUN set -eux; \
    cd /src/buildkit; go mod edit -require=github.com/moby/go-archive@v0.3.0; go mod tidy; \
    go build -mod=mod -trimpath -ldflags='-s -w' -o /out/buildkitd ./cmd/buildkitd; \
    go build -mod=mod -trimpath -ldflags='-s -w' -o /out/buildctl ./cmd/buildctl; \
    cd /src/rootlesskit; go mod edit -require=golang.org/x/crypto@v0.52.0 -require=golang.org/x/net@v0.56.0; go mod tidy; \
    CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/rootlesskit ./cmd/rootlesskit; \
    cd /src/cni; \
    CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/buildkit-cni-bridge ./plugins/main/bridge; \
    CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/buildkit-cni-host-local ./plugins/ipam/host-local; \
    CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/buildkit-cni-firewall ./plugins/meta/firewall; \
    CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/buildkit-cni-loopback ./plugins/main/loopback

FROM node:26-alpine AS node
FROM alpine:3.23
RUN apk add --no-cache bash ca-certificates fuse3 fuse-overlayfs git libgcc libstdc++ openssh openssl pigz shadow-uidmap runc xz
RUN adduser -D -u 1000 user \
    && mkdir -p /run/user/1000 /home/user/.local/tmp /home/user/.local/share/buildkit \
    && chown -R user /run/user/1000 /home/user \
    && echo user:100000:65536 | tee /etc/subuid /etc/subgid
COPY --from=buildkit /out/buildkitd /usr/bin/buildkitd
COPY --from=buildkit /out/buildctl /usr/bin/buildctl
COPY --from=buildkit /out/rootlesskit /usr/bin/rootlesskit
COPY --from=buildkit /out/buildkit-cni-bridge /usr/bin/buildkit-cni-bridge
COPY --from=buildkit /out/buildkit-cni-host-local /usr/bin/buildkit-cni-host-local
COPY --from=buildkit /out/buildkit-cni-firewall /usr/bin/buildkit-cni-firewall
COPY --from=buildkit /out/buildkit-cni-loopback /usr/bin/buildkit-cni-loopback
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=buildkit /src/buildkit/examples/buildctl-daemonless/buildctl-daemonless.sh /usr/bin/buildctl-daemonless.sh
RUN chmod 0755 /usr/bin/buildctl-daemonless.sh \
    && mkdir -p /etc/buildkit \
    && printf '%s\n' '{"cniVersion":"0.4.0","name":"buildkit","plugins":[{"type":"bridge","bridge":"buildkit0","isGateway":true,"ipMasq":true,"ipam":{"type":"host-local","subnet":"10.10.0.0/24","routes":[{"dst":"0.0.0.0/0"}]}},{"type":"loopback"}]}' > /etc/buildkit/cni.json
USER 1000:1000
ENV HOME=/home/user USER=user XDG_RUNTIME_DIR=/run/user/1000 TMPDIR=/home/user/.local/tmp BUILDKIT_HOST=unix:///run/user/1000/buildkit/buildkitd.sock
LABEL org.opencontainers.image.title="Forgejo BuildKit rootless job image"
LABEL org.opencontainers.image.source="https://forgejo.tom-mendy.com/Tom-Mendy/homelab"
LABEL org.opencontainers.image.version="1"
ENTRYPOINT []
CMD ["/bin/sh"]
