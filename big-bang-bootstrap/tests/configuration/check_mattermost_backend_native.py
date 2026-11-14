"""Explicit offline/native image check. No cluster access or real credentials.

Usage: python3 check_mattermost_backend_native.py --helm PATH --chart PATH
Requires the selected official Registry1 image already cached in podman.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
import yaml

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / 'big-bang-bootstrap/configuration/packages/mattermost'


def merge(dst, src):
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            merge(dst[key], value)
        else:
            dst[key] = value


def check(helm, chart):
    values = {}
    for name in ('candidate-values.yaml', 'backend/database-values.yaml', 'backend/lab-resources-values.yaml'):
        merge(values, yaml.safe_load((MODULE / name).read_text())['addons']['mattermost']['values'])
    with tempfile.TemporaryDirectory(prefix='mattermost-native-') as tmp:
        path = Path(tmp)
        inputs = path / 'values.yaml'
        inputs.write_text(yaml.safe_dump(values))
        rendered = subprocess.run([helm, 'template', 'mattermost', chart, '-n', 'mattermost', '-f', str(inputs)], capture_output=True, text=True, check=True)
        docs = [doc for doc in yaml.safe_load_all(rendered.stdout) if doc]
        sts = [doc for doc in docs if doc['kind'] == 'StatefulSet']
        assert len(sts) == 1
        spec = sts[0]['spec']['template']['spec']
        container = spec['containers'][0]
        assert container['image'] == 'registry1.dso.mil/ironbank/opensource/postgres/postgresql:18.6'
        security = container['securityContext']
        assert security['readOnlyRootFilesystem'] and security['runAsUser'] == 1001
        assert spec['securityContext']['fsGroup'] == 1001
        env = {item['name']: item for item in container['env']}
        assert env['POSTGRES_PASSWORD_FILE']['value'] == '/opt/bitnami/postgresql/secrets/postgres-password'
        assert 'POSTGRES_PASSWORD' not in env
        assert 'POSTGRESQL_POSTGRES_PASSWORD_FILE' not in env
        mounts = {item['mountPath']: item for item in container['volumeMounts']}
        for target in ('/tmp', '/run/postgresql', '/var/lib/postgresql/data'):
            assert target in mounts and not mounts[target].get('readOnly', False)
        secret_mount = mounts['/opt/bitnami/postgresql/secrets/'] if '/opt/bitnami/postgresql/secrets/' in mounts else mounts['/opt/bitnami/postgresql/secrets']
        # Kubernetes Secret projections are read-only even when chart omits mount.readOnly.
        assert any(v['name'] == secret_mount['name'] and v.get('secret', {}).get('secretName') == 'mattermost-postgresql-auth' for v in spec['volumes'])
        assert '.initialized' not in str(container['readinessProbe'])
        # Synthetic equivalents only. Never load a Kubernetes Secret.
        secrets = {'mattermost-postgresql-auth': {'postgres-password': 'synthetic-admin-only', 'password': 'synthetic-app-only'}}
        configs = {doc['metadata']['name']: doc.get('data', {}) for doc in docs if doc['kind'] == 'ConfigMap'}
        volumes = {v['name']: v for v in spec['volumes']}
        name = 'mattermost-native-contract-' + str(time.time_ns())
        args = ['podman', 'run', '-d', '--name', name, '--pull=never', '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--userns', 'keep-id:uid=1001,gid=1001', '--user', '1001:1001']
        for item in container['env']:
            value = item.get('value')
            if value is None:
                ref = item['valueFrom']['secretKeyRef']
                value = secrets[ref['name']][ref['key']]
            args += ['-e', item['name'] + '=' + str(value)]
        for index, mount in enumerate(container['volumeMounts']):
            volume = volumes.get(mount['name'], {})  # StatefulSet claim is not in spec.volumes.
            source = path / ('mount-' + str(index))
            source.mkdir()
            source.chmod(0o770)
            data = {}
            readonly = mount.get('readOnly', False)
            if 'secret' in volume:
                data = secrets[volume['secret']['secretName']]
                readonly = True  # Kubernetes Secret projection is always read-only.
            if 'configMap' in volume:
                data = configs[volume['configMap']['name']]
                readonly = True  # Kubernetes ConfigMap projection is always read-only.
            for key, value in data.items():
                (source / key).write_text(value)
                (source / key).chmod(0o440 if readonly else 0o640)
            args += ['-v', str(source) + ':' + mount['mountPath'] + (':ro,Z' if readonly else ':rw,Z')]
        args += [container['image']]
        if container.get('command'):
            raise AssertionError('Unexpected chart entrypoint override')
        args += container.get('args', [])
        try:
            result = subprocess.run(args, capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            for _ in range(45):
                query = subprocess.run(['podman', 'exec', name, 'psql', '-U', 'postgres', '-d', 'mattermost', '-Atc', "select rolname,rolsuper,rolcreatedb,rolcreaterole from pg_roles where rolname='mattermost'"], capture_output=True, text=True)
                if query.returncode == 0 and 'mattermost|f|f|f' in query.stdout:
                    break
                time.sleep(1)
            assert query.returncode == 0 and 'mattermost|f|f|f' in query.stdout, 'Startup/role check failed'
            for probe in ('readinessProbe', 'livenessProbe'):
                subprocess.run(['podman', 'exec', name, *container[probe]['exec']['command']], capture_output=True, check=True)
            subprocess.run(['podman', 'exec', '-e', 'PGPASSWORD=synthetic-app-only', name, 'psql', '-h', '127.0.0.1', '-U', 'mattermost', '-d', 'mattermost', '-c', 'CREATE TABLE contract_probe(id int); DROP TABLE contract_probe;'], capture_output=True, check=True)
            denied = subprocess.run(['podman', 'exec', '-e', 'PGPASSWORD=synthetic-wrong-password', name, 'psql', '-h', '127.0.0.1', '-U', 'mattermost', '-d', 'mattermost', '-c', 'SELECT 1'], capture_output=True, text=True)
            assert denied.returncode != 0 and 'password authentication failed' in denied.stderr, 'Wrong app password was not denied'
            print(json.dumps({'native_render': 'PASS', 'rendered_password_file': 'PASS', 'rendered_env_mounts_readonly_root': 'PASS', 'app_role_and_schema': 'PASS', 'rendered_probes': 'PASS'}))
        finally:
            subprocess.run(['podman', 'rm', '-f', name], capture_output=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--helm', required=True)
    parser.add_argument('--chart', required=True)
    options = parser.parse_args()
    check(options.helm, options.chart)
