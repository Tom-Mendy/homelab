#!/usr/bin/env bash

set -euo pipefail

if ! command -v kubeconform >/dev/null 2>&1
then
  echo "kubeconform is required but was not found in PATH" >&2
  exit 127
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
kubernetes_dir="$(cd "$script_dir/../kubernetes" && pwd)"
mapfile -t charts < "$kubernetes_dir/active-local-charts.txt"
tmp_dir="$(mktemp -d)"
failed=0
trap 'rm -rf "$tmp_dir"' EXIT

for c in "${charts[@]}"
do
  echo "=== $c ==="
  render_file="$tmp_dir/$c.yaml"

  helm template test "$kubernetes_dir/$c" >"$render_file"

  if ! kubeconform \
    -strict \
    -summary \
    -ignore-missing-schemas \
    "$render_file"
  then
    failed=1
  fi
done

exit "$failed"
