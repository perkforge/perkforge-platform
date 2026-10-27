# Household portal integration

The executable implementation now lives in
[`local-lab/optional/portal`](../../../local-lab/optional/portal/README.md), outside
active Fleet paths. Read its contract, generated resources, identity plan and
activation gates. The templates formerly in this directory moved with it.

Ownership remains split: `perkforge-portal` owns application/image code;
`perkforge-tenant-portal` owns the app Helm/Fleet bundle; platform owns identity,
service identities, RBAC, NetworkPolicy, admission, namespace/project/quota and
scoped Fleet registration. Household apps have no security-control exception.
See the [tenant repository boundary plan](../../TENANT-REPOSITORY-BOUNDARY.md).

Merging this MR does not deploy anything. Keycloak is paused and its existing
public issuer is HTTP; trusted HTTPS, image approval, secret delivery, namespace
capacity, network allowances and Fleet release-storage permissions remain explicit
activation gates. No client, credential, grant or live resource was created.
