# Set Up Matrix

Implemented as a local GitOps chart in `kubernetes/matrix`:

- Tuwunel with Authentik OIDC and public federation.
- Cinny at `chat.tom-mendy.com`.
- Element MatrixRTC backend at `rtc.tom-mendy.com`.
- Shared `nfs-k8s` storage and native plus Synology backups.
- Infisical delivery for OIDC, registration, LiveKit, and Hermes secrets.

The remaining operator steps (Infisical values, Pangolin resources, first admin
login, and Hermes bot registration) are documented in
`kubernetes/matrix/README.md`.
