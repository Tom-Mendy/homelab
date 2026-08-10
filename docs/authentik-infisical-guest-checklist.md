# Infisical and authentik Guest Access Checklist

This checklist is for the manual work needed after the Infisical and authentik
admin accounts exist.

## Goal

- Expose authentik publicly at `https://authentik.tom-mendy.com` through
  Pangolin.
- Keep the private/internal authentik URL available at
  `https://authentik.home.tom-mendy.com`.
- Use manual invitations for guest accounts.
- Give guests controlled access to Forgejo and later to selected apps.
- Keep Infisical private.

## Infisical

- Confirm the `homelab` project exists.
- Confirm the `prod` environment exists.
- Create or confirm these secret paths:
  - `/authentik`
  - `/forgejo`
  - `/oidc`
- Add the current authentik bootstrap values to `/authentik`:
  - `AUTHENTIK_ENABLED=true`
  - `AUTHENTIK_SECRET_KEY=<current stable value>`
  - `AUTHENTIK_LOG_LEVEL=info`
  - `AUTHENTIK_ERROR_REPORTING__ENABLED=false`
  - `AUTHENTIK_WEB__PATH=/`
- Create a Kubernetes Machine Identity for the Infisical operator.
- Enable Kubernetes Auth on that identity with:
  - namespace: `authentik`
  - service account: `authentik-infisical-sync`
  - access: read-only to `homelab/prod/authentik`
- Record the Machine Identity ID.
- After the identity works, update GitOps separately:
  - set `infisicalSecret.enabled: true`
  - set `infisicalSecret.identityID` to the recorded identity ID
- Verify the operator owns or refreshes `authentik-secrets`.
- Keep the manual Kubernetes secret until Infisical sync has been verified.

## authentik Public Access

- In authentik, confirm the instance works at:
  - `https://authentik.home.tom-mendy.com`
- In Pangolin, create a public resource:
  - public hostname: `authentik.tom-mendy.com`
  - upstream URL: `http://authentik-server.authentik.svc.cluster.local:80`
  - upstream protocol: HTTP
- In public DNS, create or verify `authentik.tom-mendy.com` points to Pangolin.
- Test from outside the LAN:
  - `https://authentik.tom-mendy.com`
- Keep `authentik.home.tom-mendy.com` as the admin recovery path.

## authentik Groups and Guests

- Create groups:
  - `homelab-admins`
  - `homelab-guests`
  - `forgejo-users`
- Add your admin account to `homelab-admins`.
- Create a guest invitation flow:
  - invitation link required
  - public self-registration disabled outside invitations
  - new users added to `homelab-guests`
- Create a test invitation for a non-admin account.
- Confirm the test guest:
  - can log in
  - cannot access authentik admin
  - only sees assigned applications

## Forgejo SSO

- In authentik, create an OIDC provider and application for Forgejo.
- Restrict application access to:
  - `homelab-admins`
  - `forgejo-users`
  - optionally `homelab-guests` if all guests should get Forgejo access
- In Forgejo, create an OpenID Connect authentication source pointing to
  authentik.
- Store Forgejo OIDC client credentials in Infisical under `/forgejo` or
  `/oidc/forgejo`.
- Keep Forgejo local login enabled until the guest login path is verified.
- Test with the guest account:
  - login through authentik
  - Forgejo account creation or account linking
  - no admin rights
  - expected repository visibility only

## Later Apps

- Configure apps one by one.
- Prefer native OIDC support.
- Use authentik proxy provider only for apps without native OIDC.
- Do not protect machine/API endpoints with browser SSO unless tested:
  - Atuin sync
  - webhooks
  - runner callbacks
  - internal service-to-service URLs

## Validation Commands

```sh
kubectl get helmreleases -n flux-system authentik infisical infisical-operator
kubectl get svc -n authentik authentik-server
kubectl get pods -n authentik
kubectl get pods -n infisical
kubectl get infisicalsecret -n authentik
kubectl get secret authentik-secrets -n authentik
```

## Browser Checks

- `https://authentik.home.tom-mendy.com`
- `https://authentik.tom-mendy.com`
- Forgejo login via authentik
- Guest account application list
