# Deploy Matrix with Tuwunel, Authentik, and MatrixRTC

Date: 2026-08-17

## Problem

The homelab needed a federated Matrix service before Hermes could be connected
to a messaging channel. Human users had to authenticate with the existing
Authentik SSO service, while Hermes needed one non-interactive local account.
The service also had to survive either Kubernetes worker being unavailable and
therefore could not use worker-local storage.

The chosen public layout is:

- Tuwunel and Matrix IDs: `matrix.tom-mendy.com`.
- Cinny web client: `chat.tom-mendy.com`.
- LiveKit and its MatrixRTC authorization service: `rtc.tom-mendy.com`.

## Reasoning and implementation

The existing local Helm chart, Flux, Authentik blueprint, Infisical, Blocky,
Homepage, Traefik, and NFS patterns were reused. This kept Matrix inside the
same GitOps lifecycle without adding another controller or secret mechanism.

Tuwunel uses one replica with a `Recreate` strategy because its RocksDB database
is a single-writer workload. Its data and online-backup PVCs both use
`nfs-k8s`, so the pod can be rescheduled between `node2` and `node3`. Cinny is
stateless. LiveKit and `lk-jwt-service` run together in one pod so their shared
configuration and lifecycle remain small. LiveKit automatic room creation is
disabled so only the authorization service can authorize room creation.

The Authentik blueprint creates the `matrix-users` group, OIDC provider, Matrix
application, and bindings for `matrix-users` and `homelab-admins`. The existing
OIDC Infisical identity distributes the OIDC client secret. A separate
`InfisicalStaticSecret` reads `/matrix` for Tuwunel registration and LiveKit
secrets; separating it prevents missing Matrix runtime access from breaking the
existing `/oidc` synchronization.

Pangolin remains an operator-side step because its raw TCP and UDP resources
and VPS firewall are outside this repository. HTTPS uses the existing Newt to
Traefik path. LiveKit additionally needs TCP 7881 and UDP 50100 through 50110
published as raw resources. Eleven UDP ports are enough for the expected small
personal workload and can be widened later in both Helm and Pangolin.

## Commands and observed results

The local chart suite, Authentik chart, Flux render, storage policy, and diff
were checked with:

```bash
./scripts/test-helm-chart.sh
helm lint kubernetes/authentik
helm template authentik kubernetes/authentik >/tmp/authentik-rendered.yaml
helm template matrix kubernetes/matrix >/tmp/matrix-rendered.yaml
kubectl kustomize kubernetes/flux/cluster \
  --load-restrictor LoadRestrictionsNone >/tmp/flux-rendered.yaml
./scripts/check-storage-policy.sh
git diff --check
```

All 24 active local charts reported `OK`. Authentik linted successfully with
only Helm's optional icon recommendation. Flux and both chart renders
completed, `git diff --check` returned no errors, and the storage checker
reported:

```text
storage policy ok
```

Kubeconform was run against the rendered Matrix resources:

```bash
docker run --rm -i ghcr.io/yannh/kubeconform:v0.7.0 \
  -strict -ignore-missing-schemas -summary </tmp/matrix-rendered.yaml
```

Result:

```text
16 resources: 16 valid, 0 invalid, 0 errors, 0 skipped.
```

The BusyBox digest initially used by the LiveKit configuration init container
was checked against the registry:

```bash
docker buildx imagetools inspect busybox:1.37.0
```

The first sandboxed attempt failed with DNS resolution disabled:

```text
dial tcp: lookup registry-1.docker.io: Temporary failure in name resolution
```

The approved network retry returned the multi-platform digest
`sha256:9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0`,
which replaced the incorrect initial value.

Two attempted client-side Kubernetes dry runs were also useful failures:

```bash
kubectl apply --dry-run=client -f /tmp/matrix-rendered.yaml
kubectl apply --dry-run=client --validate=false -f /tmp/matrix-rendered.yaml
```

Both still attempted API discovery at `10.0.0.21:6443`, which the sandbox
blocked. Kubeconform was therefore used for the offline schema validation. No
live Flux reconciliation was attempted because the required Infisical values,
Pangolin resources, and public DNS are operator-owned prerequisites.

The bot registration helper's first HMAC self-test failed because its expected
fixture accidentally represented backslash-zero text instead of NUL separators.
The fixture was corrected to the Synapse protocol's NUL-separated value, after
which both the self-test and Python bytecode compilation passed:

```bash
./scripts/register-hermes-matrix-bot.py --self-test
python3 -m py_compile scripts/register-hermes-matrix-bot.py
```

## Outcome

The repository now contains the Matrix namespace, Flux HelmRelease, local Helm
chart, Authentik OIDC application and access group, Infisical secret delivery,
internal DNS entries, Homepage link, backup coverage, a secure bot registration
helper, and an operational runbook. No active Matrix manifest uses `local-path`
or `hostPath`; both
persistent claims explicitly use `nfs-k8s`, and no node affinity prevents
rescheduling between workers.

Deployment becomes ready after the runbook's external prerequisites are
completed, the first human Authentik login creates the Tuwunel administrator,
and the local `hermes-bot` account is registered through a port-forward. Calls
use Element Desktop or Element X; TURN is deferred until testing shows it is
needed on restrictive networks.

## First deployment correction

After the first reconciliation, Cinny and MatrixRTC were ready, both NFS claims
were bound, but Tuwunel was in `CrashLoopBackOff`. Public checks consequently
returned `404` for the unhandled homeserver root, `503` for the Matrix versions
and well-known endpoints, and `200` for Cinny.

The previous Tuwunel log exposed the root cause:

```text
data did not match any variant of untagged enum Either for key "PORT" in
`TUWUNEL_` environment variable(s)
```

Kubernetes service links had injected `TUWUNEL_PORT=tcp://...` because the
Service is named `tuwunel`. Tuwunel treats every `TUWUNEL_*` variable as
configuration, so it tried and failed to parse that URL as its numeric port.
The pod now sets `enableServiceLinks: false`, fixing the shared source of those
injected variables instead of overriding one accidental value.

With that fixed, startup reached Tuwunel's registration safety check and
stopped again because `allow_registration` requires a closed registration
token even when OIDC is configured. The existing high-entropy shared
registration secret was also configured as `registration_token_file`. It
already grants the stronger shared-secret registration capability, so reusing
it satisfies the closed-registration guard without adding or exposing another
secret. Human registration remains gated by the Authentik provider policy.

The operator had also created a dedicated `matrix-k8s-auth` Infisical Machine
Identity. The chart was corrected to create `matrix-infisical-sync`, its
`InfisicalConnection`, `InfisicalAuth`, and `/matrix` static secret in the
Matrix namespace. The temporary reuse of the Authentik identity for Matrix
runtime secrets was removed; Authentik still distributes only the OIDC client
secret from `/oidc`.

The corrected render passed Helm lint and storage checks. Kubeconform found 21
resources: 18 valid Kubernetes resources and three skipped Infisical custom
resources whose schemas are not in its standard registry, with no invalid
resources or errors.

The live Deployment was patched with the service-link fix and the corrected
ConfigMap, then restarted. The first rollout-status call immediately repeated
the old `ProgressDeadlineExceeded` condition, so the new ReplicaSet and logs
were inspected directly. After the registration-token correction, rollout
completed and all three Matrix pods became ready with zero restarts. Tuwunel
opened its new RocksDB database and listened on port 8008.

Public verification then returned:

```text
matrix root:       404 (expected; no website is served there)
client versions:  200
client well-known: 200
Cinny:             200
```

The Matrix login API advertises Authentik through `m.login.sso`. A separate
remaining issue was found for `rtc.tom-mendy.com`: direct Pangolin testing
showed Traefik's default certificate and HTTP 404, while the Matrix and Chat
Pangolin resources returned 200. This identifies the RTC HTTPS Pangolin
resource or its host forwarding as the remaining external configuration issue,
not a Kubernetes pod or Ingress failure.
