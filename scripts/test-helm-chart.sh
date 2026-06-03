#!/usr/bin/env bash

set -u

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
kubernetes_dir="$(cd "$script_dir/../kubernetes" && pwd)"
mapfile -t charts < "$kubernetes_dir/active-local-charts.txt"
failed=0
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

for c in "${charts[@]}"
do
  echo "=== $c ==="

  if ! helm lint "$kubernetes_dir/$c" >"$tmp_dir/$c-lint.out" 2>"$tmp_dir/$c-lint.err"
  then
    echo "LINT FAIL"
    cat "$tmp_dir/$c-lint.out"
    cat "$tmp_dir/$c-lint.err"
    failed=1
    continue
  fi

  if ! helm template test "$kubernetes_dir/$c" >"$tmp_dir/$c-render.out" 2>"$tmp_dir/$c-render.err"
  then
    echo "TEMPLATE FAIL"
    cat "$tmp_dir/$c-render.err"
    failed=1
    continue
  fi

  echo "OK"
done

exit "$failed"
