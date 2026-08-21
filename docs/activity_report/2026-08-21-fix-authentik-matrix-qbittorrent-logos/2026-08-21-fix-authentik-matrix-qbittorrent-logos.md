# Fix Authentik Matrix and qBittorrent Logos

## Problem

The Matrix and qBittorrent application cards in the Authentik dashboard did
not display their logos. Their configured icon URLs pointed to paths that were
not valid for the deployed applications or upstream repositories.

## Reasoning and investigation

The application definitions were inspected with:

```sh
rg -n -B 5 -A 5 'id: (qbittorrent|matrix)-application|meta_icon' \
  kubernetes/authentik/blueprints/oidc-clients.yaml
```

The qBittorrent repository's Web UI references its 32-pixel icon at
`src/webui/www/private/images/qbittorrent32.png`, so the old `dist/logo` path
was replaced with that official repository path.

The Matrix deployment serves Cinny at `chat.tom-mendy.com`. The standard
root-level `/favicon.ico` path is the appropriate application favicon path;
the previous `/assets/favicon.ico` path was removed.

## Commands and results

The upstream qBittorrent icon location was confirmed from the Web UI source:

```text
<link rel="icon" type="image/png" href="images/qbittorrent32.png"
  sizes="32x32">
```

The repository was updated so the two application definitions now use:

```yaml
meta_icon: https://raw.githubusercontent.com/qbittorrent/qBittorrent/master/src/webui/www/private/images/qbittorrent32.png
meta_icon: https://chat.tom-mendy.com/favicon.ico
```

Validation commands:

```sh
git diff --check
# no output; exit status 0

helm lint kubernetes/authentik
# 1 chart(s) linted, 0 chart(s) failed

./scripts/check-storage-policy.sh
# storage policy ok

rumdl check --fix \
  docs/activity_report/2026-08-21-fix-authentik-matrix-qbittorrent-logos/2026-08-21-fix-authentik-matrix-qbittorrent-logos.md
# Success: No issues found in 1 file
```

The full-repository Markdown check still reports pre-existing issues in other
files; it does not report an issue in this new activity report.

## Outcome

The Authentik blueprint now uses the official qBittorrent Web UI icon and the
Cinny root favicon for the Matrix application. Flux reconciliation will apply
the corrected icon URLs to Authentik.
