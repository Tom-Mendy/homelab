#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "run this script as root on a Kubernetes node" >&2
  exit 1
fi

HARBOR_HOST="${HARBOR_HOST:-harbor.home.tom-mendy.com}"
HARBOR_SCHEME="${HARBOR_SCHEME:-https}"
CONTAINERD_CERTS_DIR="/etc/containerd/certs.d"

declare -A PROJECTS=(
  [docker.io]=proxy-dockerhub
  [ghcr.io]=proxy-ghcr
  [quay.io]=proxy-quay
  [registry.k8s.io]=proxy-k8s
  [lscr.io]=proxy-lscr
  [nvcr.io]=proxy-nvcr
)

install -d -m 0755 "$CONTAINERD_CERTS_DIR"

for registry in "${!PROJECTS[@]}"; do
  project="${PROJECTS[$registry]}"
  directory="$CONTAINERD_CERTS_DIR/$registry"
  install -d -m 0755 "$directory"
  target="$directory/hosts.toml"
  if [[ -f "$target" ]]; then
    cp -a "$target" "$target.harbor-backup.$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  tmp="$(mktemp "$directory/hosts.toml.XXXXXX")"
  cat >"$tmp" <<EOF
server = "https://$registry"

[host."$HARBOR_SCHEME://$HARBOR_HOST/v2/$project"]
  capabilities = ["pull", "resolve"]
  override_path = true
EOF
  chmod 0644 "$tmp"
  mv "$tmp" "$target"
done

systemctl restart containerd
systemctl is-active --quiet containerd
echo "Harbor mirror configuration installed for ${#PROJECTS[@]} registries"
