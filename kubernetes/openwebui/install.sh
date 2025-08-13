#!/usr/bin/env bash
set -e

helm repo add open-webui https://helm.openwebui.com/
helm repo update

kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.32/deploy/local-path-storage.yaml

helm upgrade --install openwebui open-webui/open-webui \
  --namespace=openwebui \
  --create-namespace \
  -f openwebui-values.yaml

kubectl apply -n openwebui -f openwebui-ingress.yaml