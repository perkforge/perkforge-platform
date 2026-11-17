"""Fixed bounded smoke check. Never print environment, tokens or host details."""
import os
from pathlib import Path


def main():
    outcome = os.environ.get('ACCEPTANCE_OUTCOME', 'success')
    if outcome not in ('success', 'failure'):
        raise SystemExit('Invalid acceptance outcome')
    if os.geteuid() == 0:
        raise SystemExit('Nonroot execution required')
    status = Path('/proc/self/status').read_text()
    caps = next(line.split()[1] for line in status.splitlines() if line.startswith('CapEff:'))
    if int(caps, 16) != 0 or Path('/var/run/secrets/kubernetes.io/serviceaccount/token').exists():
        raise SystemExit('Restricted API-free execution required')
    # Exclusive file creation refuses existing files, hardlinks and symlinks.
    fd = os.open('acceptance.txt', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write('Platform acceptance: ' + outcome + '\n')
    print('Platform acceptance: ' + outcome)
    return 0 if outcome == 'success' else 1


if __name__ == '__main__':
    raise SystemExit(main())
