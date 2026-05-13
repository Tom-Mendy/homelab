#!/usr/bin/env bash
set -euo pipefail

allowlist="scripts/storage-policy-local-path-allowlist.txt"
failed=0

while IFS=: read -r path line match; do
  if ! grep -Fxq "$path" "$allowlist"; then
    printf '%s:%s:%s\n' "$path" "$line" "$match"
    failed=1
  fi
done < <(rg -n --glob '*.yaml' --glob '*.yml' 'local-path' kubernetes || true)

if [[ "$failed" -ne 0 ]]; then
  echo
  echo "error: new local-path usage is forbidden. Use storageClassName: nfs-k8s."
  echo "Legacy allowlist entries must be removed as each PVC is migrated."
  exit 1
fi

echo "storage policy ok"
