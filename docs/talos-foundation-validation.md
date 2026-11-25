# Talos foundation validation

Executed on 2026-11-08 against the separate `talos-homelab` context.
Production applications remain on Ubuntu. CI, workspace, inference, and
background-download maintenance holds remain active.

The interrupted Cilium installation targeted the default Ubuntu context.
The Ubuntu release was exported privately and uninstalled. Calico remained
installed; node1 and node3 were Ready, their CNI directories contained only
Calico configuration, and Authentik, Forgejo, and Coder health checks passed.
Talos had received only three copied controllers and lacked their supporting
ServiceAccounts. The complete Cilium chart was installed against the explicit
Talos kubeconfig, and the controller templates were corrected to match the
Talos settings. Always supply both `--kubeconfig` and `--kube-context` to Helm.
Do not change the global default context to work around an incorrect command.

Foundation versions and configuration:

| Component | Version | Configuration |
| --- | --- | --- |
| Talos | 1.14.5 | Existing reviewed node2 configuration |
| Kubernetes | 1.36.6 | Existing VIP 10.0.0.65 |
| Cilium | 1.20.4 | [Values](../talos/cilium-values.json) |
| NFS provisioner chart | 4.0.18, application 4.0.2 | [Values](../talos/nfs-values.json) |
| MetalLB | 0.15.3 native manifest | [Pool and advertisement](../talos/metallb-config.yaml) |
| Traefik chart | 42.2.0, image 3.7.17 pinned by digest | [Values](../talos/traefik-values.json) |

Cilium uses Kubernetes IPAM and the existing kube-proxy. Flannel is absent.
Do not disable kube-proxy unless the corresponding Cilium replacement setting
is deliberately changed and tested. Cilium uses Talos's cgroup mount, removes
SYS_MODULE from agent capabilities, and enables host legacy routing for Talos
host DNS compatibility. See the
[official Cilium Talos instructions](https://docs.cilium.io/en/stable/installation/k8s-install-talos-linux/).

Disposable Pods in `talos-validation` verified pod-to-pod traffic and service
DNS. A NetworkPolicy denied ingress, then an explicit client allow restored
traffic. Both outcomes were checked, rather than inferring enforcement from
Cilium readiness. Existing CoreDNS Pods were replaced under Cilium.

The Talos `nfs-k8s` provisioner mounts Synology `10.0.0.11:/volume1/k8s/talos`
and uses the distinct provisioner identity `homelab-talos/nfs-k8s`. Its default
namespace/PVC/PV directory naming avoids production Ubuntu paths and prevents
name reuse from selecting a retained directory accidentally. Volumes use
Retain and no node affinity. A disposable PVC passed write and readback as
UID/GID 1000 after Pod replacement. Future worker-to-worker rescheduling still
needs validation once a second Talos node exists.

An initial disposable test used an unsupported `${.PV.name}` path-pattern
substitution. That pattern was removed before production use. Its old test PV
and directory are retained as evidence, alongside the successful replacement
test. Do not reuse that old test path for an application. The provisioner's
original temporary root PV is also retained; it does not contain exclusive
application data and is not the active root mount.

MetalLB advertises only the reserved Talos pool 10.0.0.70–10.0.0.89. Traefik
uses 10.0.0.70 and the nondefault `talos-traefik` ingress class. Its chart was
recovered from the deployed Ubuntu Helm chart without exporting release
credentials. This avoids a blocked chart-download path and preserves the
existing ingress version. The NFS chart was recovered in the same way.
Ubuntu Traefik 10.0.0.60 and Blocky 10.0.0.61 remain separate.

The disposable ingress host is `talos-validation.home.tom-mendy.com`.
HTTP and HTTPS were tested directly against 10.0.0.70 with the correct Host
header and TLS SNI. The private test CA was verified explicitly. This does
not validate public DNS, public certificate issuance, or production SSO.
No public DNS record or production certificate was changed for this test.

Private evidence, original exports, chart copies, test TLS key, and recovery
scripts are outside Git at:

```text
~/.local/state/homelab/talos-migration/20261108-cilium-recovery/
```

The real Talos Kubernetes access file is:

```text
~/.local/state/homelab/talos-migration/20261108T1052-node2-final/kubeconfig-talos-homelab.yaml
```

Use context `talos-homelab` with the pinned Kubernetes 1.36.6 client.
Ubuntu access files and the default context remain unchanged. Treat private
exports as credentials and never add them to Git.

Production cutover remains gated on selective GitOps and per-application
recovery, dependency, and stopped-writer checks. Do not apply Ubuntu's full
Flux application tree to Talos. Keep Forgejo, Infisical, and Authentik on
Ubuntu while preparing a narrowly scoped Talos allowlist. Retain the stale
Ubuntu node2 object until the installation and rollback decision are settled;
it is not a usable Ubuntu worker after the disk installation.

Node2 passed a full reboot with a changed boot ID. The API VIP `/readyz`,
Cilium, CoreDNS, NFS provisioner, MetalLB, and Traefik recovered. The original
NFS proof remained unchanged and HTTPS ingress passed again. A new disposable
PVC also bound after reboot, verifying provisioning rather than only an
existing mount. NetworkPolicy deny and allow checks were repeated after boot.
Transient API/CNI startup failures resolved during recovery.

The `talos-validation` namespace remains for repeatable foundation checks.
Its data is disposable; do not adopt these test PVCs for production. The test
certificate expires after seven days and is not a production TLS solution.
No production operator, application, or full Flux reconciliation was started.
Storage policy and changed-document Markdown checks passed. Repository-wide
Markdown checking still reports 146 existing issues in 21 unrelated files.

A final health check on 2026-11-11 confirmed all Talos foundation Pods Ready,
HTTPS ingress working, and the NFS proof unchanged. Ubuntu node1 and node3
were Ready, all six singleton databases had one ready instance, and Authentik,
Forgejo, and Coder health endpoints responded successfully.

The private `talos-foundation-recovery.tar.gz.age` archive preserves 42 files,
including the reviewed final machine configuration and real Talos access
files. Its decrypted bytes matched the source archive exactly. The archive
and `encrypted-recovery-check.json` reside in the private evidence directory.
