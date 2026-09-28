#!/usr/bin/env bash
set -euo pipefail

: "${CODER_URL:?CODER_URL is required}"
: "${CODER_SESSION_TOKEN:?Set the CODER_SESSION_TOKEN Forgejo Actions secret}"
: "${COMMIT_SHA:?COMMIT_SHA is required}"
: "${EVENT_NAME:?EVENT_NAME is required}"
: "${REF_NAME:?REF_NAME is required}"

if [[ "$REF_NAME" != main ]]; then
  echo "Coder templates can only be published from main" >&2
  exit 1
fi

CODER_URL="${CODER_URL%/}"
EVENT_BEFORE="${EVENT_BEFORE:-}"
version_name="$(git rev-parse --short=12 "$COMMIT_SHA")"
version_message="$(git show -s --format=%s "$COMMIT_SHA")"
templates=(agent-workspace t3code hermes-personal personal-desktop)

for template in "${templates[@]}"; do
  directory="kubernetes/coder/workspace-templates/$template"

  if [[ "$EVENT_NAME" != workflow_dispatch && -n "$EVENT_BEFORE" && "$EVENT_BEFORE" =~ [^0] ]]; then
    if git diff --quiet "$EVENT_BEFORE" "$COMMIT_SHA" -- "$directory"; then
      continue
    fi
  fi

  echo "Validating and publishing $template as $version_name"
  terraform -chdir="$directory" fmt -check -recursive
  terraform -chdir="$directory" init -backend=false -input=false -no-color
  terraform -chdir="$directory" validate -no-color

  coder templates push "$template" \
    --directory "$directory" \
    --name "$version_name" \
    --message "$version_message" \
    --activate \
    --ignore-lockfile \
    --yes

  offset=0
  page_size=100
  while true; do
    response="$(curl --fail --silent --show-error --get \
      --header "Coder-Session-Token: $CODER_SESSION_TOKEN" \
      --data-urlencode "q=template:$template" \
      --data-urlencode "limit=$page_size" \
      --data-urlencode "offset=$offset" \
      "$CODER_URL/api/v2/workspaces")"
    jq -e '.workspaces | type == "array"' >/dev/null <<<"$response"
    mapfile -t workspace_ids < <(jq -r '.workspaces[].id' <<<"$response")

    for workspace_id in "${workspace_ids[@]}"; do
      curl --fail --silent --show-error --request PUT \
        --header "Coder-Session-Token: $CODER_SESSION_TOKEN" \
        --header 'Content-Type: application/json' \
        --data '{"automatic_updates":"always"}' \
        "$CODER_URL/api/v2/workspaces/$workspace_id/autoupdates" >/dev/null
    done

    workspace_count="${#workspace_ids[@]}"
    (( workspace_count < page_size )) && break
    offset=$((offset + page_size))
  done
done
