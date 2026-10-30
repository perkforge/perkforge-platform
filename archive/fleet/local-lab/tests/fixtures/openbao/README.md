# OpenBao ingress regression fixtures

Public, credential-free fixtures captured read-only on 2026-10-28 from the
installed local RKE2 Traefik DaemonSet and `ingressroutetcps.traefik.io` CRD.
`traefik-provider.json` records only provider arguments, image and chart identity.
`ingressroutetcp-v1alpha1.schema.json` is the served v1alpha1 OpenAPI schema.
No Secret values or private cluster access material are included.

The test renders the actual Fleet support bundle, checks the route's ingress
class against the configured provider filter and validates its structure against
this installed schema. It does not execute Kubernetes-specific schema extensions
or prove live TLS routing; verified-CA/SNI checks against both existing ingress
IPs remain a post-merge acceptance step. Refresh these fixtures deliberately if
the ingress controller changes.

Upstream: https://github.com/traefik/traefik (MIT license, copied alongside).
