#!/bin/bash
set -e

# ====== CONFIG ======
# Change this IP range to match your LAN (must be free and outside DHCP range)
METALLB_IP_RANGE="192.168.1.20-192.168.1.49"
WHOAMI_DOMAIN="whoami.local"

# ====== 1. Install MetalLB ======
echo "[1/4] Installing MetalLB..."
kubectl create namespace metallb-system || true
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.5/config/manifests/metallb-native.yaml

# Wait for MetalLB pods to be ready
kubectl wait --namespace metallb-system \
  --for=condition=ready pod \
  --selector=component=controller \
  --timeout=120s

# Create IPAddressPool & L2Advertisement
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default-address-pool
  namespace: metallb-system
spec:
  addresses:
  - ${METALLB_IP_RANGE}
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: default-l2
  namespace: metallb-system
spec:
  ipAddressPools:
  - default-address-pool
EOF

# ====== 2. Install Traefik via Helm ======
echo "[2/4] Installing Traefik..."
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm uninstall traefik -n traefik || true

helm install traefik traefik/traefik \
  --namespace=traefik \
  --create-namespace \
  --set service.type=LoadBalancer \
  --set ports.websecure.tls.enabled=true

# Wait for Traefik pod to be ready
kubectl wait --namespace traefik \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/name=traefik \
  --timeout=120s

# ====== 3. Deploy test app ======
echo "[3/4] Deploying whoami test app..."
kubectl create deployment whoami --image=traefik/whoami --replicas=1 || true
kubectl expose deployment whoami --port=80 || true

# ====== 4. Create Ingress ======
echo "[4/4] Creating Ingress for whoami..."
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: whoami
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: web,websecure
spec:
  rules:
  - host: ${WHOAMI_DOMAIN}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: whoami
            port:
              number: 80
EOF

echo "✅ Setup complete!"
echo "➡ Add this line to /etc/hosts on your PC:"
echo "$(kubectl get svc -n traefik traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}') ${WHOAMI_DOMAIN}"
echo "➡ Then open: http://${WHOAMI_DOMAIN} or https://${WHOAMI_DOMAIN}"
