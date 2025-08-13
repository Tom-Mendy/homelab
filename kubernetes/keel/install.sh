#!/usr/bin/env bash
set -e
helm repo add keel https://keel-hq.github.io/keel
helm repo update

helm upgrade --install keel keel/keel \
  --namespace=keel \
  --create-namespace \
  -f keel-values.yaml

kubectl apply -n keel -f keel-ingress.yaml

# Wait for Keel pod to be ready
kubectl wait --namespace keel \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/name=keel \
  --timeout=120s
