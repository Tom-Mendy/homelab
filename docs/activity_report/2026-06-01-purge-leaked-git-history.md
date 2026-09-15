# Purge Leaked Git History

## Problem

Old commits contained leaked secrets in Kubernetes values, example files, and
activity notes. Current manifests had already moved most runtime secrets to
Infisical, but reachable Git history still needed cleanup.

## Reasoning

The target was the Forgejo `origin` remote only. The rewrite scope was all
local branches and tags.

Create a backup before rewriting:

```sh
git bundle create /tmp/homelab-before-secret-purge.bundle --all
```

Scan history and write full findings to a temporary file:

```sh
gitleaks detect --source . --no-banner \
  --report-format json \
  --report-path /tmp/homelab-gitleaks-full.json \
  --exit-code 0
```

Build a temporary `git filter-repo` replacement file from scanner secrets and
known copied WireGuard/Endfield values. Secret values were not printed.

Install `git-filter-repo` in a temporary virtual environment because it was not
installed on the system:

```sh
python3 -m venv /tmp/git-filter-repo-venv
/tmp/git-filter-repo-venv/bin/pip install git-filter-repo
```

Rewrite history:

```sh
/tmp/git-filter-repo-venv/bin/git-filter-repo \
  --replace-text /tmp/homelab-replacements.txt \
  --force
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

`git-filter-repo` removed `origin`, so it was restored:

```sh
git remote add origin forgejo:tom-mendy/homelab.git
git config lfs.https://forgejo/tom-mendy/homelab.git/info/lfs.locksverify false
```

## Changes

- Replaced scanner-detected leaked values across reachable history.
- Added extra replacements for tracked Endfield `.env` values missed by
  gitleaks.
- Removed tracked `kubernetes/endfield/.env`.
- Sanitized `kubernetes/endfield/.env.example`.
- Updated `.gitignore` so `.env` files stay ignored but `.env.example` remains
  allowed.
- Added a gitleaks pre-commit hook config.

## Verification

Gitleaks after rewrite:

```text
149 commits scanned.
no leaks found
```

Exact replacement-pattern search across all reachable history returned no
matches:

```sh
git grep -F --quiet -- "$secret" $(git rev-list --all)
```

Storage policy still passed:

```text
storage policy ok
```

## Outcome

Reachable local history no longer contains the known leaked strings. The next
step is a forced update of `origin` branches and tags, then every old clone must
be discarded and re-cloned.
