#!/bin/sh
set -eu

ready_file=/run/nymvpn/ready
access_code_file=${NYMVPN_ACCESS_CODE_FILE:-/run/secrets/nymvpn/access-code}

if [ "${1:-}" = check ]; then
  test -f "$ready_file"
  nym-vpnc status 2>/dev/null | grep -qi connected
  exit
fi

mkdir -p /run/nymvpn
rm -f "$ready_file"

# The RPC socket is private to this container; Kubernetes shares the network
# namespace with qBittorrent, not this filesystem.
nym-vpnd run-as-service --disable-client-verification &
daemon_pid=$!

cleanup() {
  rm -f "$ready_file"
  kill "$daemon_pid" 2>/dev/null || true
  wait "$daemon_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

until nym-vpnc info >/dev/null 2>&1; do
  kill -0 "$daemon_pid"
  sleep 1
done

if [ ! -s /var/lib/nym-vpnd/mainnet/access_code.json ] \
  && [ ! -s /var/lib/nym-vpnd/mainnet/mnemonic.json ]; then
  test -s "$access_code_file"
  nym-vpnc account set "$(cat "$access_code_file")"
fi

nym-vpnc tunnel set --two-hop on
nym-vpnc tunnel set --ipv6 off
nym-vpnc gateway set \
  --entry-country "${NYMVPN_ENTRY_COUNTRY:-FR}" \
  --exit-country "${NYMVPN_EXIT_COUNTRY:-CH}"
nym-vpnc lan set allow
nym-vpnc connect --wait
touch "$ready_file"

while kill -0 "$daemon_pid" 2>/dev/null; do
  if nym-vpnc status 2>/dev/null | grep -qi connected; then
    touch "$ready_file"
  else
    rm -f "$ready_file"
    nym-vpnc reconnect >/dev/null 2>&1 || true
  fi
  sleep 10
done

wait "$daemon_pid"
