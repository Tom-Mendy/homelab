{{- define "grafana-local-extras.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "grafana-local-extras.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "grafana-local-extras.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "grafana-local-extras.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "grafana-local-extras.labels" -}}
helm.sh/chart: {{ include "grafana-local-extras.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
