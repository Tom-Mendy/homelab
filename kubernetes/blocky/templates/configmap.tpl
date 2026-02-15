apiVersion: v1
kind: ConfigMap
metadata:
  name: blocky-config
  namespace: blocky
data:
  config.yml: |
{{ .Files.Get "config.yml" | nindent 4 }}
