#!/usr/bin/env sh

set -eu

output_dir="${1:-.forgejo-rendered}"

rm -rf "$output_dir"
mkdir -p "$output_dir"

while IFS= read -r chart; do
  helm template test "kubernetes/${chart}" >"${output_dir}/${chart}.yaml"
done < kubernetes/active-local-charts.txt
