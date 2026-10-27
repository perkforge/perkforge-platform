{{- define "portal.values" -}}
{{- $c := . -}}
enabled: {{ ne $c.lifecycle.state "disabled" }}
image:
  repository: {{ $c.imageRepository | quote }}
  digest: '{{ $c.imageDigest | default "" }}'
portalOrigin: {{ $c.portalOrigin | quote }}
tenantSource: disabled
identity:
  issuer: {{ $c.identity.issuer | quote }}
  clientId: {{ $c.identity.clientId | quote }}
  audience: {{ $c.identity.audience | quote }}
  existingSecret: {{ $c.identity.existingSecret | quote }}
{{- end -}}
