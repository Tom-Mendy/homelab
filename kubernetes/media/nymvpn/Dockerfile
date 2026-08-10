# syntax=docker/dockerfile:1.7
FROM ubuntu:24.04@sha256:019e8eb29a85e74d64925745884f2ec79aa27e3feab36353d24656f4d6b89467

ARG NYMVPN_VERSION=2026.10.0
ARG NYMVPN_RELEASE=nym-vpn-core-v2026.10.0

ADD --checksum=sha256:fd7c0ab9b638ffc15300697e5af8efcb4afc1ed3d8010b7523370fa90969cd3d \
  https://github.com/nymtech/nym-vpn-client/releases/download/${NYMVPN_RELEASE}/nym-vpnc_${NYMVPN_VERSION}_amd64.deb \
  /tmp/nym-vpnc.deb
ADD --checksum=sha256:408f948922e64596c9ae4c727de6e8b8c568756937dd4271c69dd9df41161afc \
  https://github.com/nymtech/nym-vpn-client/releases/download/${NYMVPN_RELEASE}/nym-vpnd_${NYMVPN_VERSION}_amd64.deb \
  /tmp/nym-vpnd.deb

RUN apt-get update \
  && apt-get install -y --no-install-recommends /tmp/nym-vpnc.deb /tmp/nym-vpnd.deb ca-certificates \
  && rm -rf /var/lib/apt/lists/* /tmp/nym-vpn*.deb

COPY --chmod=0755 entrypoint.sh /usr/local/bin/nymvpn-entrypoint

ENTRYPOINT ["/usr/local/bin/nymvpn-entrypoint"]
