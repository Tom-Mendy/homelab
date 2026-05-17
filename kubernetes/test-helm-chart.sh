#!/usr/bin/env bash

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
charts=(blocky homepage traefik keel prometheus grafana navidrome vaultwarden forgejo forgejo-runner searxng endfield infisical-postgres authentik-postgres authentik)
for c in "${charts[@]}"
do echo "=== $c ==="
helm template test "$script_dir/$c" >/tmp/helm_render.out 2>/tmp/helm_render.err
code=$?
if [[ $code -eq 0 ]]
then echo "OK"
else echo "FAIL ($code)"
cat /tmp/helm_render.err
fi
done
