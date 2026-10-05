# syntax=docker/dockerfile:1.7
FROM ubuntu:24.04@sha256:019e8eb29a85e74d64925745884f2ec79aa27e3feab36353d24656f4d6b89467

ARG NYMVPN_VERSION=2026.12.4
ARG NYMVPN_RELEASE=nym-vpn-v2026.12.4

ADD --checksum=sha256:dc1d7f43beef5cf05a2dcfa0cee6bc89b335c58bd4ac0ddaf73726cc08d49eab \
  https://github.com/nymtech/nym-vpn-client/releases/download/${NYMVPN_RELEASE}/nym-vpnc_${NYMVPN_VERSION}_amd64.deb \
  /tmp/nym-vpnc.deb
ADD --checksum=sha256:c28260de21d6f4ab486a0f37268ab9968184fbab1a6c4432e0e1fc96673c7934 \
  https://github.com/nymtech/nym-vpn-client/releases/download/${NYMVPN_RELEASE}/nym-vpnd_${NYMVPN_VERSION}_amd64.deb \
  /tmp/nym-vpnd.deb

RUN apt-get update \
  && apt-get install -y --no-install-recommends /tmp/nym-vpnc.deb /tmp/nym-vpnd.deb ca-certificates iproute2 \
  && rm -rf /var/lib/apt/lists/* /tmp/nym-vpn*.deb

ENV NYMVPN_ACCESS_CODE_FILE=/run/secrets/nymvpn/access-code

COPY --chmod=0755 entrypoint.sh /usr/local/bin/nymvpn-entrypoint

ENTRYPOINT ["/usr/local/bin/nymvpn-entrypoint"]
