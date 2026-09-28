# syntax=docker/dockerfile:1.7
FROM ubuntu:24.04@sha256:019e8eb29a85e74d64925745884f2ec79aa27e3feab36353d24656f4d6b89467

ARG NYMVPN_VERSION=2026.11.3
ARG NYMVPN_RELEASE=nym-vpn-v2026.11.3

ADD --checksum=sha256:78149d3f1cd99405042451f75a6dc9cf80d53c53b6242894292c5de7f571d835 \
  https://github.com/nymtech/nym-vpn-client/releases/download/${NYMVPN_RELEASE}/nym-vpnc_${NYMVPN_VERSION}_amd64.deb \
  /tmp/nym-vpnc.deb
ADD --checksum=sha256:0047bb2921b3f05819e7c4a7a69874157d4b618e6bf64bce87ac5829d569382c \
  https://github.com/nymtech/nym-vpn-client/releases/download/${NYMVPN_RELEASE}/nym-vpnd_${NYMVPN_VERSION}_amd64.deb \
  /tmp/nym-vpnd.deb

RUN apt-get update \
  && apt-get install -y --no-install-recommends /tmp/nym-vpnc.deb /tmp/nym-vpnd.deb ca-certificates iproute2 \
  && rm -rf /var/lib/apt/lists/* /tmp/nym-vpn*.deb

ENV NYMVPN_ACCESS_CODE_FILE=/run/secrets/nymvpn/access-code

COPY --chmod=0755 entrypoint.sh /usr/local/bin/nymvpn-entrypoint

ENTRYPOINT ["/usr/local/bin/nymvpn-entrypoint"]
