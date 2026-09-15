# Fix Forgejo OIDC required claim

## Problem

Forgejo showed an `Account is suspended` page after an authentik OIDC login.
The account was not suspended in the Forgejo database: both `is_active` was
`1` and `prohibit_login` was `0`.

## Reasoning and commands

The Forgejo request log identified the actual rejection:

```text
Failed authentication attempt ... user is not allowed login [uid: 0, ...]
```

The OAuth source had a configured required claim named `forgejo`. Forgejo
checks that claim before looking up an existing external-login link. The
declarative authentik provider only emits the standard OpenID, email, profile,
offline access, and group mappings, so it does not emit `forgejo`.

```sh
kubectl -n forgejo exec deployment/forgejo -- \
  su-exec git forgejo --config /data/gitea/conf/app.ini admin auth list
kubectl -n forgejo logs deployment/forgejo --since=30m
kubectl -n authentik exec deployment/authentik-worker -- ak shell -c \
  '... provider.property_mappings.all() ...'
```

The non-sensitive OAuth configuration result was:

```text
required_claim_name: forgejo
group_claim_name: groups
admin_group: homelab-admins
```

The active source was updated immediately with the same arguments as the
declarative startup script. Its verified non-sensitive state is now:

```text
required_claim_name:
group_claim_name: groups
admin_group: homelab-admins
```

The first self-test invocation attempted to execute the mounted ConfigMap file
directly and returned `exec format error`. The deployment intentionally invokes
it through `/bin/sh`; running the test through that interpreter succeeds.

## Outcome

The Forgejo OIDC setup script now explicitly clears both required-claim fields
on every create or update. The existing authentik application policy remains
the access control boundary, while the standard `groups` claim continues to
grant Forgejo administration to `homelab-admins`.
