#!/usr/bin/env bash

charts=(blocky homepage traefik keel prometheus grafana navidrome vaultwarden forgejo searxng)
for c in "${charts[@]}"
do echo "=== $c ==="
helm template test "$c" >/tmp/helm_render.out 2>/tmp/helm_render.err
code=$?
if [[ $code -eq 0 ]]
then echo "OK"
else echo "FAIL ($code)"
cat /tmp/helm_render.err
fi
done