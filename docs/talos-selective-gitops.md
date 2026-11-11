# Talos selective GitOps

Executed on 2026-11-11. Production applications remain on Ubuntu.
The Talos application allowlist is empty. The initial reconciliation manages
only a validation ConfigMap and cannot deploy an application.

The dedicated branch is `migration/talos-bootstrap-20261111`. Talos reads
commit `8ab8a9cea3955ba5418ac2c2c6fff7f59af0e7e8`, rather than tracking branch
updates automatically. The workstation branch and Ubuntu's pinned Git source
were not changed. The migration commit contains only the isolated bootstrap
and validation manifests added for this stage.

[Flux Operator values](../talos/bootstrap/flux-operator-values.json) disable
the web interface. Operator 0.61.0 installs Flux 2.9.6 through the separate
[FluxInstance](../talos/bootstrap/flux-instance.yaml). Only source-controller,
kustomize-controller, and helm-controller are installed. Image automation is
absent. The instance has no sync entry that could create an additional root.

The [source and reconciliation definition](../talos/bootstrap/sync.yaml)
selects only `talos/gitops/root`. The GitRepository artifact was inspected:
it contains exactly `kustomization.yaml` and `validation.yaml` under that path.
It excludes Ubuntu's entire `kubernetes/` application tree. The root has
`prune: false` and uses a dedicated
[restricted reconciler](../talos/bootstrap/reconciler-rbac.yaml).

Live authorization checks confirmed the reconciler can create ConfigMaps in
`talos-gitops-validation` and cannot create Secrets, Deployments, or
HelmReleases. A harmless ConfigMap drift test verified that Flux restores the
committed value. Do not broaden these permissions casually to add an app.
Introduce each application through its own reviewed source path, identity,
resources, dependencies, and cutover procedure.

Forgejo remains on Ubuntu. The temporary
[SSH bridge](../talos/bootstrap/ubuntu-forgejo-bridge.json) is an Ubuntu-only
Service at `10.0.0.62:22`. It selects the existing Forgejo Pod and exposes no
HTTP endpoint. This IP belongs to Ubuntu's .60–.64 pool, outside Talos's
.70–.89 pool. This bridge is a temporary cross-cluster dependency. Remove it
only after Talos has another working Git source. Never add the bridge to the
Talos root or deploy it using the Talos context.

The bridge SSH host key was compared with Ubuntu Flux's trusted Forgejo key
before use. Forgejo deploy key ID 3, `talos-flux-readonly-20261111`, is a
separate read-only repository key. Talos Secret `flux-system/talos-forgejo-readonly`
contains its private key and verified known_hosts. The Ubuntu key was not
reused. Neither private key nor a credential-bearing Secret belongs in Git.
Forgejo Actions remain disabled during the maintenance hold.

Recovery material and operation evidence are private:

```text
~/.local/state/homelab/talos-migration/20261111-selective-gitops/
```

Use the real Talos kubeconfig documented in the
[foundation record](talos-foundation-validation.md). Always pass the explicit
kubeconfig and context `talos-homelab` to Helm, kubectl, and Flux. Apply the
bridge only with Ubuntu's separate access file and context. The existing
workstation default remains Ubuntu.

Recover the GitOps bootstrap in this order:

1. Verify the Talos foundation, API, DNS, and NFS checks.
2. Restore the temporary Ubuntu Forgejo bridge if still needed and verify its
   SSH host key against the preserved known_hosts file.
3. Install the pinned operator chart with the Talos-specific values. Recover
   the chart from the private archive if its original download is unavailable.
4. Apply the FluxInstance and reconciler RBAC files using the Talos context.
5. Recreate the read-only Git Secret from the preserved key and known_hosts,
   without writing Secret YAML into the repository.
6. Apply `sync.yaml`. Verify both GitRepository and Kustomization Ready at the
   recorded commit, then check the validation ConfigMap and authorization.

To stop reconciliation, suspend `Kustomization/talos-bootstrap` in namespace
`flux-system`. It has pruning disabled, so suspension preserves existing
objects. Do not uninstall production Ubuntu Flux or resume its maintenance
holds as part of this rollback. Revoke deploy key ID 3 and delete the bridge
only when no active Talos source uses them.

Portfolio is the first application candidate. Its cutover still requires:

- Capture the live Ubuntu image digest and deploy that same content on Talos.
- Provision only its scoped Harbor pull credential. Do not copy broad
  Infisical administrator credentials to bootstrap a registry pull.
- Prepare a Talos-specific release with ingress class `talos-traefik`, a test
  hostname, and no automatic image updates. Do not import the Ubuntu release
  unchanged, because its ingress class and certificate resolver differ.
- Validate the image pull, readiness, content, security settings, and HTTPS
  through the Talos ingress before changing public traffic.
- Determine the actual public routing path, including Cloudflare and any
  Newt/Pangolin route, and establish the target certificate strategy. The
  disposable foundation certificate is not a public production certificate.
- Preserve the Ubuntu endpoint and release for a verified traffic rollback.
  Record cutover and observation before starting another application.

Applications requiring Infisical Kubernetes authentication need a separate
Talos identity and a token-review configuration for the Talos CA/API. Ubuntu
ServiceAccount JWTs and reviewer settings do not authenticate the new cluster.
Those application-specific identities remain prerequisites, not a completed
secret-migration claim. Forgejo, Infisical, and Authentik remain on Ubuntu.
