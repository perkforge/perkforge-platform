#!/usr/bin/env python3
"""Plan or explicitly bootstrap development-only Nextcloud credentials; never rotate."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
NAMESPACE = 'tenant-home-nextcloud'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='requires operator approval for development bootstrap')
    parser.add_argument('--kubectl', default='kubectl')
    args = parser.parse_args()
    if not args.apply:
        print('PLAN: retain existing credentials; create only missing nextcloud-admin and nextcloud-db-app Secrets.')
        print('Passwords live under ignored platform .secrets/nextcloud/. No resources changed.')
        return 0
    os.umask(0o077)
    directory = ROOT / '.secrets/nextcloud'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink():
        raise ValueError('Refusing symlink credential directory')
    os.chmod(directory, 0o700)
    def run(*command, data=None):
        result = subprocess.run([args.kubectl, *command], input=data, text=True, capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError('Kubernetes operation failed; credential values suppressed')
        return result.stdout
    ns = json.loads(run('get', 'namespace', NAMESPACE, '-o', 'json'))
    labels = ns['metadata'].get('labels', {})
    if labels.get('platform.perkforge.io/tenant') != 'home' or labels.get('platform.perkforge.io/classification') != 'protected':
        raise ValueError('Refusing bootstrap outside the protected Home namespace')
    for name, username in [('nextcloud-admin', 'home-admin'), ('nextcloud-db-app', 'nextcloud')]:
        # No secret payload is read or printed during existence checks.
        exists = run('get', 'secret', name, '-n', NAMESPACE, '--ignore-not-found', '-o', 'name').strip()
        password_file = directory / (name + '-password')
        if password_file.is_symlink():
            raise ValueError('Refusing symlink password file')
        if exists:
            if not password_file.is_file() or not password_file.read_text().strip():
                raise ValueError('Existing Secret lacks its local credential record; recover explicitly, do not rotate')
            print(f'Retained existing {name}; no rotation.')
            continue
        if password_file.exists():
            password = password_file.read_text().strip()
            if not password:
                raise ValueError('Empty credential record; refusing rotation')
        else:
            password = secrets.token_hex(24)
            fd = os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(password + '\n')
        os.chmod(password_file, 0o600)
        document = {'apiVersion':'v1', 'kind':'Secret',
                    'metadata':{'name':name,'namespace':NAMESPACE,
                                'labels':{'platform.perkforge.io/tenant':'home'}},
                    'type':'Opaque', 'immutable':True,
                    'stringData':{'username':username,'password':password}}
        # create, not apply: never overwrite an existing Secret, including races.
        run('create', '-f', '-', data=json.dumps(document))
        print(f'Created {name}; credential values suppressed.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        print('Bootstrap stopped; no credentials printed. Check namespace ownership, connectivity, and private local records.', file=sys.stderr)
        sys.exit(1)
