{{- define "traefik-local-extras.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "traefik-local-extras.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "traefik-local-extras.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "traefik-local-extras.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "traefik-local-extras.labels" -}}
helm.sh/chart: {{ include "traefik-local-extras.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
