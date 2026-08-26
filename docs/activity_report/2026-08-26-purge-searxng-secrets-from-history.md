# Purge SearXNG secrets from Git history

## Problem

Forgejo validation job 90 failed during the Gitleaks step. It found two old
SearXNG values in `kubernetes/searxng/values.yaml`:

- `serverSecretKey`
- `wireguardPrivateKey`

The current values file already contains empty placeholders and Infisical
delivers the runtime secrets. The old values were still reachable from the
`main` branch history, so changing the current file would not fix the scan.

## Reasoning path

Inspect the failed job and current repository state:

```sh
sed -n '1,260p' homelab-validation-validate-90.log
git status --short
nl -ba kubernetes/searxng/values.yaml | sed -n '30,52p'
```

Observed results:

```text
Finding: serverSecretKey
File: kubernetes/searxng/values.yaml
Line: 34

Finding: wireguardPrivateKey
File: kubernetes/searxng/values.yaml
Line: 45
```

The current file contained only empty strings. The failed job used
`fetch-depth: 0`, so Gitleaks scanned history as well as the current tree.

Confirm that the old commits were still ancestors of `main`:

```sh
for c in 270dae3 1c1ef96 5bd7cc1 6987c9e fbbb181; do
  git merge-base --is-ancestor "$c" main && echo "$c is reachable"
done
```

The SearXNG commits and the earlier documented purge commit were reachable.
The earlier purge had changed current files and documentation, but had not
rewritten Git history.

Create a recovery bundle before rewriting:

```sh
git bundle create /tmp/homelab-before-searxng-history-rewrite.bundle --all
git bundle verify /tmp/homelab-before-searxng-history-rewrite.bundle
```

Result:

```text
The bundle records a complete history.
The bundle uses this hash algorithm: sha1
/tmp/homelab-before-searxng-history-rewrite.bundle is okay
```

Install `git-filter-repo` in `/tmp`, then rewrite the published `main` and
`wakapi` refs. The replacement expressions were extracted from the historical
SearXNG values without printing the secret values:

```sh
/tmp/homelab-git-filter-repo-venv/bin/git-filter-repo \
  --force \
  --replace-text <(for commit in $(git rev-list main -- \
    kubernetes/searxng/values.yaml); do
    git show "$commit:kubernetes/searxng/values.yaml" 2>/dev/null || true
  done | awk -F': ' '$1 ~ /serverSecretKey|wireguardPrivateKey/ && \
    $2 != "\"\"" {
    value=$2
    gsub(/^"|"$/, "", value)
    if (value != "") print "literal:" value "==>***REMOVED***"
  }' | sort -u) \
  --refs refs/heads/main refs/remotes/origin/main \
  refs/remotes/origin/HEAD refs/remotes/origin/wakapi
```

The first attempt failed because the sandbox exposed `.git` as read-only. The
same command succeeded with the required elevated filesystem permission:

```text
Parsed 277 commits
HEAD is now at d59a873 document newt probe fix
New history written in 0.06 seconds...
Completely finished after 0.06 seconds.
```

The unrelated pre-existing deletion of `backlogs/setup-matrix.md` was restored
after the rewrite.

## Verification

The rewritten branch no longer reached the original SearXNG commits:

```text
270dae3 not reachable
1c1ef96 not reachable
5bd7cc1 not reachable
6987c9e not reachable
fbbb181 not reachable
```

A Gitleaks scan of the working directory still found the old values because
local T3 checkpoint refs and the existing stash were intentionally not
rewritten. Those refs are not published by Forgejo. A fresh single-branch
clone matching the CI checkout passed:

```text
272 commits scanned.
scanned ~2398219 bytes (2.40 MB) in 281ms
no leaks found
```

Helm lint and rendering passed for all 24 active charts:

```text
=== searxng ===
OK
...
=== vaultwarden ===
OK
```

Kubeconform passed after allowing the container to access its public schemas:

```text
Summary: 192 resources found in 24 files - Valid: 157, Invalid: 0,
Errors: 0, Skipped: 35
```

The first Kubeconform attempt failed because the container could not resolve
`raw.githubusercontent.com`. The retry with host networking passed.

The storage policy check passed:

```text
storage policy ok
```

## Validation job 91

Validation job 91 still found the same two commits after `main` had been
rewritten. The runner reported 330 commits scanned. The current local `main`
was clean, so the published branch heads were checked:

```sh
git ls-remote origin 'refs/heads/main' 'refs/heads/wakapi' 'refs/tags/*'
```

Before the update, Forgejo reported:

```text
50362beb7f476ab3fa2cce1176a82237c853399a refs/heads/main
77ba42ab95c85709f5c0bd136d73f9cdfe9a228b refs/heads/wakapi
```

`main` already used the rewritten history. `wakapi` still pointed to the old
history and was the cause of the full-history scan finding the leaked commits.

Force-update the stale branch with lease protection:

```sh
tip=77ba42ab95c85709f5c0bd136d73f9cdfe9a228b
git push origin \
  refs/heads/main:refs/heads/main \
  refs/remotes/origin/wakapi:refs/heads/wakapi \
  --force-with-lease=refs/heads/main:50362beb7f476ab3fa2cce1176a82237c853399a \
  --force-with-lease=refs/heads/wakapi:"$tip"
```

Forgejo accepted the update:

```text
+ 77ba42a...313f8d9 origin/wakapi -> wakapi (forced update)
```

The remote branches now report the rewritten heads:

```text
50362beb7f476ab3fa2cce1176a82237c853399a refs/heads/main
313f8d9b7a7db87f215dfed456c2a71a05185b62 refs/heads/wakapi
```

Verify all published branches from a fresh clone:

```sh
git clone --no-tags git@forgejo.tom-mendy.com:Tom-Mendy/homelab.git /tmp/homelab-remote-validation
gitleaks detect --source /tmp/homelab-remote-validation --redact --no-banner --verbose
```

Result:

```text
274 commits scanned.
scanned ~2409627 bytes (2.41 MB) in 236ms
no leaks found
```

## Final outcome

The published branch history now has the two SearXNG values removed while the
CI workflow continues to scan full history. The local recovery bundle is at
`/tmp/homelab-before-searxng-history-rewrite.bundle`.

The rewritten `main` and `wakapi` refs are now published in Forgejo, and a
fresh clone passes the full-history Gitleaks scan. Existing clones must be
discarded or recloned afterward. The two affected credentials must also be
rotated or revoked in Infisical because the old values were exposed in Git
history.
