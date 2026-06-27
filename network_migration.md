0. État actuel, avant toute migration

  Tout doit rester comme aujourd’hui :

  - Bbox : 192.168.1.254, accès Internet OK.
  - Netgear : 192.168.1.252, accessible en admin.
  - NAS Synology : 192.168.1.1, accessible.
  - Kubernetes :
      - node1 192.168.1.11
      - node2 192.168.1.12
      - node3 192.168.1.13

  - MetalLB : 192.168.1.20-192.168.1.49.
  - Blocky : 192.168.1.21.
  - Ton PC peut encore accéder à l’ancien réseau 192.168.1.0/24.

  Ne change rien dans le repo tant que cet état n’est pas stable.

1. Configurer le Netgear en futur routeur LAN

  État requis avant :

  - Tu es connecté à l’interface Netgear.
  - Tu peux revenir à l’interface Bbox si besoin.
  - Aucun appareil critique ne dépend encore du futur réseau 10.0.0.0/24.

  À faire sur Netgear :

  - LAN Netgear : 10.0.0.1/24.
  - DHCP : 10.0.0.100-10.0.0.240.
  - Réservations préparées :
      - NAS : 10.0.0.11
      - node1 : 10.0.0.21
      - node2 : 10.0.0.22
      - node3 : 10.0.0.23
      - Blocky : 10.0.0.53
      - MetalLB : 10.0.0.60-10.0.0.89

  DNS DHCP temporaire : Netgear ou Bbox, pas encore Blocky.

2. Migrer quelques clients non critiques

  État requis avant :

  - Netgear donne bien des IPs en 10.0.0.x.
  - Internet marche depuis le Netgear.
  - Bbox fonctionne toujours.

  Migrer seulement :

  - téléphone
  - laptop secondaire
  - TV
  - IoT non critique

  Vérifier sur un client :

  ip route
  ping -c 3 10.0.0.1
  ping -c 3 1.1.1.1
  curl -I https://example.com

  Ne migre pas NAS/Kubernetes tant que ça n’est pas stable.

3. Migrer le NAS Synology

  État requis avant :

  - Clients simples OK en 10.0.0.0/24.
  - Netgear DHCP stable.
  - Tu sais accéder à l’admin Synology.
  - Kubernetes peut encore fonctionner sur l’ancien réseau pendant la bascule.

  À faire :

  - Donner au NAS 10.0.0.11.
  - Vérifier SMB/Web.
  - Vérifier NFS :

  showmount -e 10.0.0.11

  État attendu après :

  - NAS accessible sur 10.0.0.11.
  - NFS OK.
  - Ancienne IP 192.168.1.1 ne doit plus être la référence cible.

4. Modifier le repo pour le NAS/NFS

  État requis avant :

  - NAS déjà stable en 10.0.0.11.
  - Kubernetes pas encore migré, ou au minimum encore administrable.
  - Tu acceptes que les manifests GitOps commencent à viser la nouvelle IP NAS.

  Modifs repo :

  - remplacer nfsServer: 192.168.1.1 par 10.0.0.11
  - remplacer le serveur NFS du provisioner par 10.0.0.11
  - garder storageClassName: nfs-k8s

  Check :

  ./scripts/check-storage-policy.sh

5. Migrer les nodes Kubernetes

  État requis avant :

  - NAS NFS OK en 10.0.0.11.
  - Netgear a les réservations DHCP/statiques des nodes.
  - Tu as accès physique ou IPMI/écran/clavier si une node disparaît.
  - Tu ne fais pas ça pendant qu’un service important est en cours d’écriture lourde.

  Ordre conseillé :

  1. node3 worker
  2. node2 worker
  3. node1 control-plane en dernier

  Après chaque node :

  kubectl get nodes -o wide
  kubectl get pods -A -o wide

  État attendu :

  - Les nodes reviennent en Ready.
  - Leurs IPs deviennent :
      - node1 10.0.0.21
      - node2 10.0.0.22
      - node3 10.0.0.23

6. Modifier le repo pour les IPs Kubernetes

  État requis avant :

  - Les nodes répondent déjà sur leurs IPs 10.0.0.x.
  - kubectl get nodes -o wide confirme les nouvelles IPs.
  - Ansible peut joindre les nouvelles IPs.

  Modifs repo :

  - ansible/inventory.ini
  - README.md
  - docs/network-diagram.md
  - kubernetes/kube-config-documentation.md si encore utilisé
  - tout 192.168.1.11/.12/.13 actif

  Check :

  ansible -i ansible/inventory.ini all -m ping
  kubectl get nodes -o wide

7. Migrer MetalLB et Blocky

  État requis avant :

  - Kubernetes fonctionne sur 10.0.0.x.
  - NAS/NFS OK.
  - Tu peux encore résoudre temporairement via DNS routeur/Bbox.
  - Traefik et Blocky sont sains avant changement.

  Modifs repo :

  - MetalLB : 10.0.0.60-10.0.0.89
  - Blocky service IP : 10.0.0.53
  - DNS mappings *.home.tom-mendy.com vers l’IP Traefik choisie, par exemple 10.0.0.60

  Vérifier :

  kubectl get svc -A
  dig @10.0.0.53 openwebui.home.tom-mendy.com
  curl -k --resolve openwebui.home.tom-mendy.com:443:10.0.0.60 https://openwebui.home.tom-mendy.com

8. Donner Blocky comme DNS DHCP final

  État requis avant :

  - Blocky répond en 10.0.0.53.
  - Les domaines internes résolvent correctement.
  - Traefik répond sur la nouvelle IP MetalLB.
  - Internet marche même avec Blocky comme DNS.

  À faire sur Netgear :

  - DNS DHCP principal : 10.0.0.53.
  - DNS secondaire temporaire possible : 1.1.1.1 ou 9.9.9.9.

  État attendu :

  - Les clients reçoivent 10.0.0.53 comme DNS.
  - *.home.tom-mendy.com marche sans /etc/hosts.

9. Nettoyage final

  État requis avant :

  - Tous les services critiques marchent en 10.0.0.0/24.
  - Plus aucun client important ne dépend de 192.168.1.x.

  À faire :

  rg "192\\.168\\.1" .
  nmap -sn 10.0.0.0/24
  ./scripts/check-storage-policy.sh

  Garder seulement les références historiques dans docs/activity_report/ si elles décrivent l’ancien état.

  Le point critique : ne change le repo Kubernetes qu’après que l’équipement correspondant ait déjà son IP finale. Pour le NAS surtout : d’abord 10.0.0.11
  réel et NFS OK, ensuite seulement les manifests.
