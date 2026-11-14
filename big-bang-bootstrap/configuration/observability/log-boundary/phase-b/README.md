# Controlled Portal log query acceptance

This local target binds the verified native Grafana organization 2 (`PerkForge
Portal`) to `loki-portal` and the existing exact read-only identity
`pf-log-portal-read`. The server gateway fixes its scope to `portal-runtime-v1`;
client-supplied headers and LogQL labels do not grant another scope. The namespace
lifecycle guard must already bind the registered Portal namespace UID/context and
scope. Reverify that binding before activation; namespace reuse is not migration.

Layer `profile.yaml` after the Phase A profile using the same boundary renderer.
Its complete generated boundary values must differ only in the exact reader map.
The datasource and native org2 pod-log dashboard add unique environment/map/provider keys; existing platform, legacy pilot,
Prometheus, OAuth, dashboards and alert routing remain unchanged. Organization ID
is target configuration, not embedded into a rebuilt application image.

This does not enable tenant OAuth mapping or add human memberships. Before either
is exposed, verify an actual benign Portal marker in its own partition; other
namespace records/forged scope headers must stay inaccessible; query credentials
must not push. Verify the org2 Viewer token cannot access the platform datasource
or other organizations, including direct proxy API requests, and revoke the
bounded test account/token afterwards. Retain anonymous and raw-backend denial
checks. A platform administrator reading the datasource is not tenant evidence.

The existing genuine marker was generated from the deployed Portal image with
no mounted credentials/API token and removed after positive partition capture.
Neither that result nor offline gateway tests alone complete tenant acceptance.
Keep #38 open until the remaining integrated/lifecycle/retention criteria pass.
