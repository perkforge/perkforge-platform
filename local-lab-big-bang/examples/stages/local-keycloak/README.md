# Keycloak startup stage

This stage adds the pinned Keycloak/PostgreSQL package to `local-headlamp`, leaving
Headlamp private and its OIDC configuration unchanged. It uses the separately
approved foundations and external inputs described in
[the identity trial](../local-identity/README.md).

Select this path first; switch the **same** Big Bang/root to `local-identity` only
after HTTPS issuer readiness, realm setup and Kubernetes API trust are verified.
No automatic source/root update or activation is included in this PR.
