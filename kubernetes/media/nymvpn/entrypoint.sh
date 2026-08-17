#!/bin/sh
set -eu

ready_file=/run/nymvpn/ready
initialized_file=/run/nymvpn/initialized
access_code_file=${NYMVPN_ACCESS_CODE_FILE:-/run/secrets/nymvpn/access-code}
pod_cidr=${NYMVPN_POD_CIDR:-}

is_connected() {
  printf '%s\n' "$1" | grep -Eqi '^State:[[:space:]]+Connected([[:space:]]|$)'
}

should_reconnect() {
  printf '%s\n' "$1" | grep -Eqi '^State:[[:space:]]+(Disconnected|Error)([[:space:]:]|$)'
}

if [ "${1:-}" = self-test ]; then
  is_connected 'State: Connected'
  ! is_connected 'State: Disconnected'
  ! is_connected 'State: Connecting wg, resolving api addresses, try #0'
  should_reconnect 'State: Error: unavailable'
  should_reconnect 'State: Disconnected'
  ! should_reconnect 'State: Connecting wg, awaiting account readiness, try #0'
  exit
fi

if [ "${1:-}" = startup ]; then
  test -f "$initialized_file"
  nym-vpnc info >/dev/null
  exit
fi

default_route=$(ip -4 route show default | head -n 1)
lan_gateway=$(printf '%s\n' "$default_route" | awk '{ for (i = 1; i <= NF; i++) if ($i == "via") print $(i + 1) }')
lan_interface=$(printf '%s\n' "$default_route" | awk '{ for (i = 1; i <= NF; i++) if ($i == "dev") print $(i + 1) }')
test -n "$lan_gateway"
test -n "$lan_interface"

ensure_pod_route() {
  [ -z "$pod_cidr" ] || ip -4 route replace "$pod_cidr" via "$lan_gateway" dev "$lan_interface"
}

if [ "${1:-}" = check ]; then
  test -f "$ready_file"
  nym-vpnc status 2>/dev/null | grep -qi connected
  [ -z "$pod_cidr" ] || ip -4 route show "$pod_cidr" | grep -q "dev $lan_interface"
  exit
fi

mkdir -p /run/nymvpn
rm -f "$initialized_file" "$ready_file"

# The RPC socket is private to this container; Kubernetes shares the network
# namespace with qBittorrent, not this filesystem.
nym-vpnd run-as-service --disable-client-verification &
daemon_pid=$!

cleanup() {
  rm -f "$initialized_file" "$ready_file"
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
nym-vpnc connect || true
ensure_pod_route
touch "$initialized_file"

while kill -0 "$daemon_pid" 2>/dev/null; do
  status=$(nym-vpnc status 2>/dev/null || true)
  if is_connected "$status"; then
    ensure_pod_route
    touch "$ready_file"
  else
    rm -f "$ready_file"
    ensure_pod_route
    if should_reconnect "$status"; then
      nym-vpnc reconnect || nym-vpnc connect || true
    fi
  fi
  sleep 10
done

wait "$daemon_pid"
