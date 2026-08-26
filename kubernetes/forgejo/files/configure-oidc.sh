#!/bin/sh
set -eu

find_auth_id() {
  awk -F '\t' '$2 == "authentik" { print $1; exit }'
}

forgejo_admin() {
  su-exec "${USER_UID:-1023}:${USER_GID:-100}" forgejo --config /data/gitea/conf/app.ini admin auth "$@"
}

if [ "${1:-}" = "--self-test" ]; then
  fixture='ID	Name	Type	Enabled
10	authentik	OAuth2	true'
  test "$(printf '%b\n' "$fixture" | find_auth_id)" = "10"
  test -z "$(printf 'ID\tName\tType\tEnabled\n' | find_auth_id)"
  exit 0
fi

# ponytail: retry the local CLI until Forgejo has initialized its config and DB.
attempt=0
while [ "$attempt" -lt 60 ]; do
  if auth_list="$(forgejo_admin list 2>/dev/null)"; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done

if [ "${auth_list+x}" != x ]; then
  echo "Forgejo did not become ready for OIDC configuration" >&2
  exit 1
fi

auth_id="$(printf '%s\n' "$auth_list" | find_auth_id)"
set -- \
  --name authentik \
  --provider openidConnect \
  --key forgejo \
  --secret "$FORGEJO_OIDC_CLIENT_SECRET" \
  --auto-discover-url \
  https://authentik.home.tom-mendy.com/application/o/forgejo/.well-known/openid-configuration \
  --scopes openid \
  --scopes profile \
  --scopes email \
  --scopes offline_access \
  --required-claim-name "" \
  --required-claim-value "" \
  --group-claim-name groups \
  --admin-group homelab-admins

if [ -n "$auth_id" ]; then
  forgejo_admin update-oauth --id "$auth_id" "$@"
else
  forgejo_admin add-oauth "$@"
fi
