# Talos version and network preparation

Prepared on 2026-11-07. The secret-free allocation and version lock is
[migration-plan.json](../talos/migration-plan.json). Generated credentials and
machine configurations remain outside Git at
`/home/tmendy/.local/state/homelab/talos-migration/20261107T162636Z-talos-network/`.
Use these new candidates instead of the July configurations or earlier
schema-only candidates. No Talos configuration was applied to a machine.

The baseline is Talos v1.14.5 and Kubernetes v1.36.6, on amd64. Talos 1.14 is the
current community-supported line in the [support matrix][support], and supports
Kubernetes 1.36. The older candidate's Talos v1.13.4 is superseded. Kubernetes
stays on the candidate's 1.36 minor with its available patch release. The
[Kubernetes release schedule][kubernetes] lists 1.36 support through June 2027.
Application versions and the Ubuntu cluster were not upgraded.

The matching talosctl v1.14.5 binary was downloaded from the [official release][release]
and its SHA-256 matched GitHub's release-asset digest. A separate kubectl v1.36.6
binary matched the published checksum. Both are stored in the private preparation
directory; system tools and default contexts were not replaced.
Registry checks confirmed amd64 images for the kubelet, API server, controller
manager, scheduler, and proxy at v1.36.6. Their digests are recorded privately.

Talos 1.14 uses the Image Factory metal installer, rather than the historical
`ghcr.io/siderolabs/installer` reference. The selected empty schematic is
`376567988ad370138ad8b2698212367b8edcb69b5fd68c80be1f2ec7d603b4ba`.
The installer manifest is pinned by digest in the version lock and candidates.
Its corresponding node2 boot ISO URL is:

```text
https://factory.talos.dev/image/376567988ad370138ad8b2698212367b8edcb69b5fd68c80be1f2ec7d603b4ba/v1.14.5/metal-amd64.iso
```

Download and verify the boot asset before the maintenance window. The empty
schematic has no additional hardware extensions. Node3's later GPU conversion
requires a separate NVIDIA extension/image validation before migration; the
generic candidate does not establish GPU readiness. Follow the
[Image Factory boot-asset procedure][assets] for hardware-specific variants.

| Purpose | Reserved addresses | Current state |
| --- | --- | --- |
| Ubuntu MetalLB | 10.0.0.60-10.0.0.64 | Applied and checked |
| Ubuntu Traefik | 10.0.0.60 | Preserved |
| Ubuntu Blocky | 10.0.0.61 | Preserved |
| Talos Kubernetes API VIP | 10.0.0.65 | DNS prepared; no announcement yet |
| Unallocated spare addresses | 10.0.0.66-10.0.0.69 | Keep free |
| Talos MetalLB | 10.0.0.70-10.0.0.89 | Reserved; target manifest staged |
| Talos ingress | 10.0.0.70 | Reserved within target pool |
| Talos DNS | 10.0.0.71 | Reserved within target pool |

The Ubuntu pool previously reserved .60-.89 and only .60 and .61 were allocated.
The live pool and [its bootstrap manifest](../kubernetes/metallb/metallb-config.yaml)
now reserve .60-.64. Existing service allocations were unchanged. All MetalLB
speaker and controller stale-configuration metrics remained zero after the
change. Do not restore the historical .60-.89 Ubuntu pool during coexistence.
Rollback may expand Ubuntu only after Talos reservations and announcements have
been removed and their addresses are confirmed unused.

These allocations reuse the original MetalLB reservation. The documented router
DHCP range is .100-.240; this task did not modify the router. Keep all infrastructure
ranges excluded from DHCP, and recheck router exclusions and address conflicts
before boot. No ping response is not proof that an address is unreserved.

The new DNS-only Cloudflare A record is
`talos-api.home.tom-mendy.com -> 10.0.0.65`, TTL 300. Both 1.1.1.1 and current
Blocky at 10.0.0.61 returned only that address. No round-robin node records or
Ubuntu backend are used by this endpoint. During node2 release, the Ubuntu
`kube.home.tom-mendy.com` record was moved from .22 to node1 at 10.0.0.21,
removing its dependency on node2's API proxy. Never use it for Talos bootstrap.
No application ingress or Authentik hostname was changed.

All candidates use a Talos-owned Layer2VIPConfig on alias `lan0`. Each alias
selects the wired NIC by the permanent MAC observed over read-only SSH on Ubuntu.
Static addresses remain node1 .21, node2 .22, and node3 .23 on the same /24 LAN,
with gateway .1. Host DNS uses 1.1.1.1 and 9.9.9.9 to avoid a dependency on Ubuntu
Blocky during bootstrap. The Kubernetes node IP is restricted to its own /32,
so the kubelet cannot select the floating VIP. Control planes accept workloads,
and their generated external-load-balancer exclusion label is removed.

The target Pod network is 10.244.0.0/16 and service network is 10.96.0.0/12.
Neither overlaps the LAN, Ubuntu's live Calico pool 10.233.64.0/18, or its service
network 10.233.0.0/18. Distinct CIDRs do not create cross-cluster routing or DNS.
Any temporary dependency between clusters still needs a reachable LAN endpoint.
Generated defaults include Flannel for bootstrap. Before production applications,
validate the chosen CNI and NetworkPolicy enforcement; default Flannel alone
does not provide that enforcement. Do not reconcile the application tree yet.

The [Talos VIP procedure][vip] requires shared layer-2 connectivity and working
etcd. The VIP becomes reachable only after bootstrap. The isolated
`base/talosconfig` therefore targets node2 directly at 10.0.0.22 for management.
Do not add still-Ubuntu nodes to its endpoint list. Add node3 and node1 only after
each joins Talos. Never use the VIP as the sole Talos management endpoint.

Repeat the preparation checks without changing a node:

```sh
uv run scripts/check-talos-preparation.py \
  --candidates /private/talos-preparation \
  --talosctl /private/talos-preparation/talosctl-linux-amd64
```

This verifies the pinned client, three schemas, component versions, endpoint,
certificate SANs, NIC selectors, static addresses, distinct CIDRs and pools,
Ubuntu's live allocations, and DNS answers. It deliberately requires the pending
disk selector and always reports `installation_approved: false`. Once the disk
is confirmed, retain a separate final reviewed configuration and inspection
record rather than silently overwriting these preparatory candidates.

For node2's ISO inspection, after the migration gates and physical console are
ready, use the pinned client against the ISO's maintenance-mode address:

```sh
/private/talos-preparation/talosctl-linux-amd64 \
  --nodes 10.0.0.22 get disks --insecure
/private/talos-preparation/talosctl-linux-amd64 \
  --nodes 10.0.0.22 get links --insecure
```

If the ISO receives a different address, use that observed address instead.
Confirm the machine identity, wired NIC MAC, disk model, serial, capacity, and
installation target from the ISO. Do not select a disk by enumeration order or
size alone. Candidates retain a nonmatching
`REPLACE_ME_AFTER_TALOS_ISO_DISK_CHECK` selector and `wipe: false`; neither makes
installation nondestructive. Applying an installation configuration can erase
the selected disk. Replace the selector with the uniquely confirmed disk
identity only in the final reviewed copy, validate it with the pinned client,
and record the inspection before applying anything. No automatic apply/reset
command is included in the preparation checker.

Bootstrap node2 once using its direct address. The new Kubernetes kubeconfig
must use `https://talos-api.home.tom-mendy.com:6443` and its own cluster CA.
Keep it separate from Ubuntu and test TLS and `/readyz` before changing any
default context. Live Talos API health, VIP ownership and failover, CNI, ingress,
and NFS recovery are installation gates, not results of this preparation.

The [target MetalLB manifest](../talos/metallb-config.yaml) is outside the Ubuntu
GitOps tree. Install the target controller and CRDs first, verify the explicit
kubeconfig's API URL and CA, then apply that manifest only to Talos. Test a
disposable service in the target pool while confirming Ubuntu .60 and .61 remain
reachable. Reserve .70 and .71 explicitly for ingress and DNS when installing
them. Never use MetalLB to provide the bootstrap API VIP.

Updated candidates, their shared secrets, isolated Talos management credentials,
and the version lock are encrypted in `talos-network-preparation.tar.gz.age` in
the private preparation directory. The existing external recovery identity is
unchanged. The earlier encrypted backup set remains intact. Keep the new archive
with the migration recovery set; it supersedes the earlier Talos candidate
archive for installation preparation.

See [the migration tracker](talos-migration.md) and
[the capacity profile](talos-node2-capacity.md). Preparation is complete;
disk confirmation and live installation checks remain mandatory.

[support]: https://docs.siderolabs.com/talos/v1.14/getting-started/support-matrix
[release]: https://github.com/siderolabs/talos/releases/tag/v1.14.5
[kubernetes]: https://kubernetes.io/releases/patch-releases/
[assets]: https://docs.siderolabs.com/talos/v1.14/platform-specific-installations/boot-assets
[vip]: https://docs.siderolabs.com/talos/v1.14/networking/advanced/vip
