# Proven PXE serving and recovery components

Start at [the active PXE entry](../README.md) and
[worker-1 readiness](../../infrastructure/TOMORROW-READINESS.md), not old proposals.
This directory retains the proven transport code; it is not a second installer.

- `templates/`, `prepare.yml`: reviewed proxy-DHCP/TFTP/nginx/guard rendering.
- `pilot.sh`, activation/rearm/shutdown YAML and identity helpers: existing exact
  session/recovery compatibility. Retarget/review worker files before any launch;
  old control-1 activation inputs are not worker authority.
- `stage-media.sh`, `install-nginx.yml`: retained preparation code and regression
  coverage; neither reinstallation nor media staging is automatically required.
- `packet-fixture.yml`, packet helpers, `tests/`: evidence-producing transport and
  lifecycle regression checks. Running native packet fixture needs separate approval.
- [HANDOFF.md](HANDOFF.md): actual prior physical checkpoint and recovery state.
- [history/](history/README.md): superseded proposals, retired console path and
  incomplete VM experiment; preserved, outside the active workflow.

No working activation/shutdown/helper file moved. Existing private runtime/media/
logs and `.secrets` recovery snapshots remain untouched. No live operation follows
from cleanup, and no generic VM runner is a prerequisite for worker-1.
