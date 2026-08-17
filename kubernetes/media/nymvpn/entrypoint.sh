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

rotation_due() {
  [ "$1" -ge 60 ]
}

if [ "${1:-}" = self-test ]; then
  is_connected 'State: Connected'
  ! is_connected 'State: Disconnected'
  ! is_connected 'State: Connecting wg, resolving api addresses, try #0'
  should_reconnect 'State: Error: unavailable'
  should_reconnect 'State: Disconnected'
  ! should_reconnect 'State: Connecting wg, awaiting account readiness, try #0'
  rotation_due 60
  ! rotation_due 59
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
connect_pid=

start_connect() {
  (nym-vpnc connect || true) &
  connect_pid=$!
}

stop_connect() {
  if [ -n "$connect_pid" ] && kill -0 "$connect_pid" 2>/dev/null; then
    kill "$connect_pid" 2>/dev/null || true
    wait "$connect_pid" 2>/dev/null || true
  fi
  connect_pid=
}

cleanup() {
  rm -f "$initialized_file" "$ready_file"
  stop_connect
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
entry_country=${NYMVPN_ENTRY_COUNTRY:-FR}
exit_country=${NYMVPN_EXIT_COUNTRY:-CH}
nym-vpnc gateway set --entry-country "$entry_country"
nym-vpnc lan set allow

exit_gateway_id=
select_exit_gateway() {
  gateway_ids=$(nym-vpnc gateway list-filtered wg \
    --country "$exit_country" --min-score medium --table-style blank 2>/dev/null \
    | awk 'length($1) >= 40 { print $1 }' || true)
  next_gateway_id=$(printf '%s\n' "$gateway_ids" \
    | awk -v current="$exit_gateway_id" 'length($1) >= 40 && $1 != current { print $1; exit }')
  if [ -n "$next_gateway_id" ]; then
    nym-vpnc gateway set --exit-id "$next_gateway_id"
    exit_gateway_id=$next_gateway_id
    return 0
  fi
  nym-vpnc gateway set --exit-country "$exit_country"
  exit_gateway_id=
}

rotate_gateway() {
  reason=$1
  printf '%s\n' "rotating NymVPN exit gateway in $exit_country ($reason)" >&2
  stop_connect
  timeout 10 nym-vpnc disconnect 2>/dev/null || true
  select_exit_gateway || true
  start_connect
  attempt_started=$(date +%s)
}

select_exit_gateway
start_connect
ensure_pod_route
touch "$initialized_file"
attempt_started=$(date +%s)

while kill -0 "$daemon_pid" 2>/dev/null; do
  now=$(date +%s)
  status=$(nym-vpnc status 2>/dev/null || true)
  if is_connected "$status"; then
    ensure_pod_route
    touch "$ready_file"
    attempt_started=$now
  else
    rm -f "$ready_file"
    ensure_pod_route
    if should_reconnect "$status"; then
      rotate_gateway "state"
    elif rotation_due "$((now - attempt_started))"; then
      rotate_gateway "timeout"
    fi
  fi
  sleep 10
done

wait "$daemon_pid"
