# Fix Hermes PATH in Coder SSH sessions

## Problem

The Hermes Coder workspace reached the `READY` lifecycle state and accepted
SSH connections, but the interactive login shell could not find `hermes`:

```console
$ hermes
/bin/sh: 1: hermes: not found
```

## Reasoning and commands

The running container was inspected before changing the template. Hermes was
present and executable, while the SSH login shell had a shorter `PATH`:

```console
$ kubectl -n coder-workspaces exec "$pod" -- sh -lc \
    'printf "PATH=%s\n" "$PATH"; command -v hermes || true; \
     find / -type f -name hermes -perm -111 2>/dev/null | head -20'
PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games
/opt/hermes/bin/hermes
/opt/hermes/.venv/bin/hermes
/opt/hermes/hermes
```

The container's main process retained the image's correct environment, and the
absolute launcher worked:

```console
$ tr '\0' '\n' </proc/1/environ | grep '^PATH='
PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:/opt/data/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

$ /opt/hermes/bin/hermes --version
Hermes Agent v0.18.0 (2026.7.1) · upstream 7c1a0295
Project: /opt/hermes
Python: 3.13.5
OpenAI SDK: 2.24.0
```

`/etc/profile` was the root cause. Debian resets `PATH` for every non-root
login shell, and the persistent `/opt/data` home had no `.profile` to restore
the image paths afterward. The workspace startup script now appends one exact,
idempotent export to `/opt/data/.profile`. Existing profile content is
preserved, and repeated workspace starts do not duplicate the line.

## Validation results

The first local Terraform validation failed because the locked providers had
not been downloaded into this working tree:

```console
$ terraform -chdir=kubernetes/coder/workspace-templates/hermes-personal validate
Error: missing or corrupted provider plugins
```

Initializing the directory and repeating all static checks succeeded:

```console
$ terraform -chdir=kubernetes/coder/workspace-templates/hermes-personal \
    init -backend=false -input=false
Terraform has been successfully initialized!

$ terraform fmt -check \
    kubernetes/coder/workspace-templates/hermes-personal/main.tf

$ terraform -chdir=kubernetes/coder/workspace-templates/hermes-personal validate
Success! The configuration is valid.

$ ./scripts/check-storage-policy.sh
storage policy ok

$ rumdl check --fix \
    docs/activity_report/2026-08-17-fix-hermes-ssh-path
Success: No issues found in 1 file
```

The repository-required `rumdl check --fix .` also ran. It reported 332
pre-existing findings and automatically changed seven unrelated files. Those
out-of-scope formatting edits were restored exactly; only this activity report
is included in the final change.

An isolated login-profile test found the launcher. Piping the version output to
`head` caused Hermes to report a harmless `BrokenPipeError`, so the final SSH
test retained the complete output instead.

The corrected template was published and activated, then the existing
workspace was updated. Terraform removed and recreated the Deployment and
Coder agent while retaining the existing NFS PVC:

```console
$ coder templates push hermes-personal \
    --directory kubernetes/coder/workspace-templates/hermes-personal \
    --message 'Restore Hermes PATH in SSH login shells' --yes
Updated version at Aug 17 10:30:47!

$ coder update nainjoueur/hermes
Apply complete! Resources: 2 added, 0 changed, 1 destroyed.

$ coder list
WORKSPACE            TEMPLATE         STATUS   HEALTHY  OUTDATED
nainjoueur/hermes    hermes-personal  Started  true     false
```

The same SSH route used by the operator passed end to end:

```console
$ ssh main.hermes.nainjoueur.coder \
    'command -v hermes && hermes --version'
/opt/hermes/bin/hermes
Hermes Agent v0.18.0 (2026.7.1) · upstream 7c1a0295
Project: /opt/hermes
Python: 3.13.5
OpenAI SDK: 2.24.0
```

## Final outcome

The persistent login profile restores the Hermes launcher and virtual
environment paths for Coder SSH sessions. No image rebuild, elevated
privilege, worker-local storage, or Kubernetes security exception was needed.
The workspace is running the active template version and remains healthy.
