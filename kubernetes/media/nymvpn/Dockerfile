# syntax=docker/dockerfile:1.7
FROM ubuntu:24.04@sha256:019e8eb29a85e74d64925745884f2ec79aa27e3feab36353d24656f4d6b89467

ARG NYMVPN_VERSION=2026.11.0
ARG NYMVPN_RELEASE=nym-vpn-v2026.11.0

ADD --checksum=sha256:6b4d1d34352149878e4f9bfb0c2b0cb84b662f784308a1d0e42cab72bc811cc2 \
  https://github.com/nymtech/nym-vpn-client/releases/download/${NYMVPN_RELEASE}/nym-vpnc_${NYMVPN_VERSION}_amd64.deb \
  /tmp/nym-vpnc.deb
ADD --checksum=sha256:1ebb58a65b3b896befb721cc174364e7044c54cd60aee5fe6e9517c97008e967 \
  https://github.com/nymtech/nym-vpn-client/releases/download/${NYMVPN_RELEASE}/nym-vpnd_${NYMVPN_VERSION}_amd64.deb \
  /tmp/nym-vpnd.deb

RUN apt-get update \
  && apt-get install -y --no-install-recommends /tmp/nym-vpnc.deb /tmp/nym-vpnd.deb ca-certificates iproute2 \
  && rm -rf /var/lib/apt/lists/* /tmp/nym-vpn*.deb

COPY --chmod=0755 entrypoint.sh /usr/local/bin/nymvpn-entrypoint

ENTRYPOINT ["/usr/local/bin/nymvpn-entrypoint"]
