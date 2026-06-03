#!/usr/bin/env bash
set -euo pipefail

allowlist="scripts/storage-policy-local-path-allowlist.txt"
failed=0

find_local_path_usage() {
  if command -v rg >/dev/null 2>&1; then
    rg -n --glob '*.yaml' --glob '*.yml' 'local-path' kubernetes || true
    return
  fi

  while IFS= read -r -d '' manifest; do
    grep -Hn 'local-path' "$manifest" || true
  done < <(find kubernetes -type f \( -name '*.yaml' -o -name '*.yml' \) -print0)
}

while IFS=: read -r path line match; do
  if ! grep -Fxq "$path" "$allowlist"; then
    printf '%s:%s:%s\n' "$path" "$line" "$match"
    failed=1
  fi
done < <(find_local_path_usage)

if [[ "$failed" -ne 0 ]]; then
  echo
  echo "error: new local-path usage is forbidden. Use storageClassName: nfs-k8s."
  echo "Legacy allowlist entries must be removed as each PVC is migrated."
  exit 1
fi

echo "storage policy ok"
