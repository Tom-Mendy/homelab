#!/usr/bin/env bash
set -e

kubectl label nodes node-3 gpu=true
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#configuration
# https://github.com/NVIDIA/k8s-device-plugin#prerequisites

helm repo add otwld https://helm.otwld.com/
helm repo update

helm upgrade --install ollama otwld/ollama \
  --namespace=ollama \
  --create-namespace \
  -f ollama-values.yaml

kubectl apply -n ollama -f ollama-ingress.yaml