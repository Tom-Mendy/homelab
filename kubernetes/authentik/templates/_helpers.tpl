{{- define "authentik-local.serverServiceName" -}}
{{- printf "%s-server" .Values.authentik.fullnameOverride -}}
{{- end -}}

{{- define "authentik-local.outpostAnnotations" -}}
traefik.ingress.kubernetes.io/router.entrypoints: web, websecure
traefik.ingress.kubernetes.io/router.tls: "true"
traefik.ingress.kubernetes.io/router.tls.certresolver: letsencrypt
{{- end -}}
