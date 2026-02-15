{{- define "keel-local-extras.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "keel-local-extras.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "keel-local-extras.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "keel-local-extras.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "keel-local-extras.labels" -}}
helm.sh/chart: {{ include "keel-local-extras.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
