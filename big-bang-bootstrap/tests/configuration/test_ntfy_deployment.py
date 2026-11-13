"""Unselected ntfy source checks; no cluster or real credentials."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import uuid
import jinja2
import yaml

BASE = Path(__file__).resolve().parents[2] / 'configuration/packages/ntfy'

def render():
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters['to_json'] = json.dumps
    return list(yaml.safe_load_all(env.from_string((BASE/'deployment.yaml.j2').read_text()).render(
        ntfy_namespace='fixture', ntfy_base_url='https://localhost:8443',
        ntfy_tls_secret='synthetic-tls', ntfy_storage_class='fixture',
        ntfy_storage_size='1Gi', ntfy_cache_duration='10m')))

class NtfyDeployment(unittest.TestCase):
    def test_scope_and_deny_defaults(self):
        docs = render()
        self.assertEqual([d['kind'] for d in docs], ['ServiceAccount','ConfigMap','Service','StatefulSet'])
        config = yaml.safe_load(docs[1]['data']['server.yml'])
        self.assertEqual(config['auth-default-access'], 'deny-all')
        self.assertEqual(config['listen-http'], '-')
        self.assertFalse(config['enable-signup'])
        for key in ['attachment-cache-dir','upstream-base-url']:
            self.assertEqual(config[key], '')
        self.assertEqual(config['web-root'], 'disable')
        self.assertNotIn('auth-users', config)
        self.assertEqual(docs[2]['spec']['type'], 'ClusterIP')

    def test_single_persistent_nonroot_instance(self):
        spec = render()[3]['spec']
        self.assertEqual(spec['replicas'], 1)
        self.assertEqual(set(spec['persistentVolumeClaimRetentionPolicy'].values()), {'Retain'})
        pod = spec['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['nodeSelector'], {'storage.perkforge.io/worker':'true'})
        self.assertTrue(pod['securityContext']['runAsNonRoot'])
        container = pod['containers'][0]
        self.assertTrue(container['securityContext']['readOnlyRootFilesystem'])
        self.assertFalse(container['securityContext']['allowPrivilegeEscalation'])
        self.assertIn('@sha256:', container['image'])
        self.assertIn('umask 077', container['args'][0])
        self.assertEqual(spec['volumeClaimTemplates'][0]['spec']['accessModes'], ['ReadWriteOnce'])
        self.assertEqual(pod['volumes'][1]['secret']['defaultMode'], 0o440)

    @unittest.skipUnless(os.environ.get('RUN_NTFY_DEPLOYMENT_NATIVE') == '1', 'opt-in native container smoke')
    def test_native_nonroot_tls_start_and_anonymous_denial(self):
        docs = render(); container = docs[3]['spec']['template']['spec']['containers'][0]
        name = 'pf-ntfy-candidate-' + uuid.uuid4().hex[:12]
        def run(*args, check=True):
            return subprocess.run(args, check=check, capture_output=True, text=True, timeout=30)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); path.chmod(0o755)
            (path/'data').mkdir(mode=0o777); (path/'data').chmod(0o777)
            (path/'server.yml').write_text(docs[1]['data']['server.yml'])
            run('openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(path/'tls.key'),
                '-out',str(path/'tls.crt'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost')
            (path/'tls.key').chmod(0o644)  # disposable synthetic key, never production
            try:
                run('podman','run','-d','--name',name,'--pull=never','--network=none',
                    '--user','1000:1000','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges',
                    '--tmpfs','/tmp:rw,size=16m','-v',f'{path}/server.yml:/etc/ntfy/server.yml:ro',
                    '-v',f'{path}/tls.crt:/etc/ssl/cert.pem:ro','-v',f'{path}/tls.key:/tls/tls.key:ro','-v',f'{path}/tls.crt:/tls/tls.crt:ro',
                    '-v',f'{path}/data:/data','--entrypoint','/bin/sh',container['image'],
                    '-ec',container['args'][0])
                ready = False
                for _ in range(30):
                    result = run('podman','exec',name,'wget','-qO-',
                                 'https://localhost:8443/v1/health',check=False)
                    if result.returncode == 0:
                        ready = True; break
                    time.sleep(1)
                self.assertTrue(ready, 'native TLS health failed')
                denied = run('podman','exec',name,'wget','-S','-O-',
                             'https://localhost:8443/tenant-portal-alerts/json?poll=1',check=False)
                self.assertNotEqual(denied.returncode, 0)
                self.assertIn('403', denied.stderr)
                denied_post = run('podman','exec',name,'wget','-S','-O-',
                                  '--post-data=synthetic-probe',
                                  'https://localhost:8443/tenant-portal-alerts',check=False)
                self.assertNotEqual(denied_post.returncode, 0)
                self.assertIn('403', denied_post.stderr)
            finally:
                run('podman','rm','-f',name,check=False)
