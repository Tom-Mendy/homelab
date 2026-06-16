# migrate from ISP provider router as main router to own router

---

## Concernant ta future migration Bouygues → Netgear

Je pense que c'est une excellente idée.

L'objectif est justement :

```text
ISP box
    ↓
Netgear (vrai routeur)
    ↓
Switch
    ↓
Cluster Kubernetes
NAS
PC
WiFi
```

et non :

```text
Bouygues box
    ↓
Tout dépend de la box
```

Les avantages :

### Changement d'opérateur transparent

Aujourd'hui :

```txt
Bouygues → Orange
```

oblige souvent à refaire :

- DHCP ;
- réservations IP ;
- DNS ;
- port forwarding ;
- VLAN ;
- firewall.

Avec un Netgear :

```txt
Bouygues Box
(mode bridge ou DMZ)
       ↓
Netgear
```

tu ne touches quasiment à rien lorsque tu changes d'ISP.
