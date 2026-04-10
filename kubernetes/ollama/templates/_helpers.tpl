{{- define "ollama-local.labels" -}}
app.kubernetes.io/name: ollama
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "ollama-local.selectorLabels" -}}
app: ollama
app.kubernetes.io/name: ollama
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}