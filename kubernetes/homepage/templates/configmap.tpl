apiVersion: v1
kind: ConfigMap
metadata:
  name: homepage-config
  namespace: homepage
data:
  services.yaml: |
{{ .Files.Get "services.yaml" | nindent 4 }}
