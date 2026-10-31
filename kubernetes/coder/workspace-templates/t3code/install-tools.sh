#!/bin/bash
# Reconstruct disposable tools at startup; explicit updates share the same lock.
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/.opencode/bin:$PATH"
cache_root="${TMPDIR:-/tmp}/t3code-local"
mkdir -p "$cache_root" "$HOME/.local/bin"
exec 9>"$cache_root/tool-install.lock"
flock -w 600 9
update=false
if [[ ${1:-} == --update ]]; then
  update=true
  shift
fi
if [[ $# == 0 ]]; then
  set -- t3 codex opencode
fi
for tool in "$@"; do
  case "$tool" in
    t3) url=https://t3.codes/install.sh; interpreter=sh ;;
    codex) url=https://chatgpt.com/codex/install.sh; interpreter=sh ;;
    opencode) url=https://opencode.ai/v2/install; interpreter=bash ;;
    *) printf 'Unknown tool: %s\n' "$tool" >&2; exit 2 ;;
  esac
  if ! "$update" && timeout 15 "$tool" --version >/dev/null 2>&1; then
    continue
  fi
  installer=$(mktemp "${TMPDIR:-/tmp}/coder-install-XXXXXX")
  trap 'rm -f "$installer"' EXIT
  # Download fully before execution. A failed curl must never run a partial script.
  curl --fail --show-error --silent --location --connect-timeout 10 \
    --max-time 120 --retry 2 --retry-max-time 180 --retry-all-errors \
    --output "$installer" "$url"
  timeout 300 "$interpreter" "$installer"
  rm -f "$installer"
  trap - EXIT
  if [[ "$tool" == opencode ]]; then
    ln -sfn "$HOME/.opencode/bin/opencode" "$HOME/.local/bin/opencode"
  fi
  timeout 15 "$tool" --version
 done
