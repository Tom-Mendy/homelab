# Migrate MetalLB and Blocky IPs

## Problem

After moving the Kubernetes nodes to `10.0.0.0/24`, the LoadBalancer services
still used the old `192.168.1.0/24` addresses:

```text
traefik              192.168.1.20
blocky               192.168.1.21
keel                 192.168.1.22
newt-main-tunnel     192.168.1.23
```

Those IPs had to move into the new MetalLB range.

## Reasoning and Commands

The active services were checked first:

```sh
kubectl --tls-server-name=node1 get svc -A -o wide
```

The MetalLB pool was changed from:

```text
192.168.1.20-192.168.1.49
```

to:

```text
10.0.0.60-10.0.0.89
```

The chosen service IPs were:

```text
traefik              10.0.0.60
blocky               10.0.0.61
keel                 10.0.0.62
newt-main-tunnel     10.0.0.63
```

The live MetalLB pool was applied:

```sh
kubectl --tls-server-name=node1 apply -f kubernetes/metallb/metallb-config.yaml
```

Blocky DNS mappings were changed so internal hostnames resolve to the new
Traefik IP:

```text
*.home.tom-mendy.com -> 10.0.0.60
```

Blocky was restarted after updating its ConfigMap:

```sh
kubectl --tls-server-name=node1 -n blocky rollout restart deployment/blocky
```

## Results

Keel and Newt moved immediately:

```text
keel                 10.0.0.62
newt-main-tunnel     10.0.0.63
```

Traefik initially stayed `pending` because both `spec.loadBalancerIP` and the
MetalLB annotation were set. Removing `spec.loadBalancerIP` fixed it:

```text
traefik              10.0.0.60
```

Blocky was rolled back by Argo CD while the Git remote still contained the old
annotation. The repository change was committed and pushed so Argo CD can keep
Blocky on:

```text
blocky               10.0.0.61
```

## Outcome

The repository now describes the new MetalLB pool and Blocky DNS mappings. The
live services expose the new VIPs:

```text
traefik              10.0.0.60
blocky               10.0.0.61
keel                 10.0.0.62
newt-main-tunnel     10.0.0.63
```

Blocky resolves internal hostnames to the new Traefik IP:

```text
forgejo.home.tom-mendy.com -> 10.0.0.60
argocd.home.tom-mendy.com  -> 10.0.0.60
```
