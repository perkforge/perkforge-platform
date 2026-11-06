"""Real Ansible against synthetic CLI state; no real credentials or cluster access."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'configuration/ansible/logging-inputs.yaml'
PASSWORD = 'ab12' * 24


class LoggingInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.private = self.folder / 'private'
        self.private.mkdir(mode=0o700)
        for name, value in [('username', 'fixture-admin'), ('password', PASSWORD)]:
            path = self.private / name
            path.write_text(value)
            path.chmod(0o600)
        hashed = subprocess.run(['openssl', 'passwd', '-6', '-stdin'], input=PASSWORD, text=True, capture_output=True, check=True).stdout.strip()
        (self.private / 'htpasswd').write_text('fixture-admin:' + hashed)
        (self.private / 'htpasswd').chmod(0o600)
        self.tls = self.folder / 'tls'; self.tls.mkdir(mode=0o700)
        self.ca = self.folder / 'ca.crt'
        def openssl(*args):
            subprocess.run(['openssl', *map(str, args)], check=True, capture_output=True)
        openssl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', self.folder / 'ca.key', '-out', self.ca, '-days', '60', '-subj', '/CN=Synthetic-only')
        self.ca.chmod(0o600)
        self.fingerprint = subprocess.run(['openssl', 'x509', '-in', str(self.ca), '-noout', '-fingerprint', '-sha256'], capture_output=True, text=True, check=True).stdout.strip().split('=')[1].replace(':', '').lower()
        for leaf, host in [('gateway', 'logging-loki-gateway.logging.svc.cluster.local'), ('backend', 'logging-loki.logging.svc.cluster.local')]:
            folder = self.tls / leaf; folder.mkdir(mode=0o700)
            openssl('req', '-newkey', 'rsa:2048', '-nodes', '-keyout', folder / 'tls.key', '-out', folder / 'leaf.csr', '-subj', '/CN=' + host)
            (folder / 'ext').write_text('subjectAltName=DNS:' + host + '\nextendedKeyUsage=serverAuth\n')
            openssl('x509', '-req', '-in', folder / 'leaf.csr', '-CA', self.ca, '-CAkey', self.folder / 'ca.key', '-CAcreateserial', '-out', folder / 'tls.crt', '-days', '60', '-extfile', folder / 'ext')
            for name in ('tls.key', 'tls.crt'): (folder / name).chmod(0o600)
        shutil.copyfile(ROOT / 'configuration/ansible/logging-input-manifests.yaml', self.folder / 'logging-input-manifests.yaml')
        self.state = self.folder / 'state.json'
        self.state.write_text(json.dumps({'secrets': {}, 'calls': [], 'uid': 'expected-uid'}))
        self.bin = self.folder / 'bin'; self.bin.mkdir()
        self.play = self.folder / 'logging-inputs.yaml'; shutil.copyfile(PLAY, self.play)
        # Mock only publication lookup; production always includes verify-release.yaml.
        (self.folder / 'verify-release.yaml').write_text('- ansible.builtin.set_fact:\n    config_release:\n      resolvedCommit: "' + 'a' * 40 + '"\n')
        (self.bin / 'git').write_text('#!/bin/sh\ncase "$*" in *rev-parse*) printf "%s\\n" aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa;; *status*) exit 0;; *) exit 99;; esac\n')
        (self.bin / 'git').chmod(0o700)
        script = '''#!/usr/bin/python3
import base64,json,os,sys
from pathlib import Path
p=Path(os.environ['METRICS_FAKE_STATE']);s=json.loads(p.read_text());args=sys.argv[1:]
def save():p.write_text(json.dumps(s))
if 'create' in args:
 doc=json.load(sys.stdin);dry='--dry-run=server' in args
 s['calls'].append(['dry-run' if dry else 'create',doc['metadata']['name']]);save()
 if s.get('reject_validation') and dry:sys.exit(1)
 if not dry:s['secrets'][doc['metadata']['namespace'] + '/' + doc['metadata']['name']]=doc;save()
 print('validated' if dry else 'created');sys.exit(0)
s['calls'].append(['get',args]);save()
if 'kube-system' in args:print(s['uid'])
elif 'namespace' in args:
 name=args[args.index('namespace')+1];print(json.dumps({'metadata':{'name':name,'labels':{'app.kubernetes.io/managed-by':'Ansible','pod-security.kubernetes.io/enforce':'privileged' if name=='monitoring' else 'restricted','pod-security.kubernetes.io/enforce-version':'v1.36'}}}))
elif 'flux-system' in args:
 auth=base64.b64encode(b'fixture:synthetic-registry-only').decode()
 data=base64.b64encode(json.dumps({'auths':{'registry1.dso.mil':{'auth':auth}}}).encode()).decode()
 print(json.dumps({'type':'kubernetes.io/dockerconfigjson','data':{'.dockerconfigjson':data}}))
else:
 name=args[args.index('-n')+1]+'/'+args[args.index('get')+2]
 if name in s['secrets']:print(json.dumps(s['secrets'][name]))
'''
        (self.bin / 'kubectl').write_text(script); (self.bin / 'kubectl').chmod(0o700)
        self.inventory = self.folder / 'inventory.yaml'
        self.inventory.write_text('all:\n  children:\n    bootstrap_clusters:\n      hosts:\n        local:\n          ansible_connection: local\n      vars:\n        deployment_environment: local\n        impact_profile: il2\n        target_kubeconfig: /synthetic/kubeconfig\n        target_context: synthetic\n        expected_cluster_uid: expected-uid\n')

    def run_play(self, apply=False, check=False, stage=None):
        variables = {'logging_inputs_apply': apply, 'logging_private_dir': str(self.private), 'logging_tls_dir': str(self.tls), 'logging_ca_file': str(self.ca), 'logging_expected_ca_sha256': self.fingerprint}
        if stage is not None:
            variables['gitops_path'] = './big-bang-bootstrap/clusters/' + stage
        env = {**os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH'], 'KUBECONFIG': '/dev/null',
               'METRICS_FAKE_STATE': str(self.state), 'SSL_CERT_DIR': str(self.folder / 'ambient-trust'), 'ANSIBLE_LOCAL_TEMP': str(self.folder / 'ansible-temp'),
               'ANSIBLE_REMOTE_TEMP': str(self.folder / 'ansible-remote')}
        result = subprocess.run(['ansible-playbook', '-i', str(self.inventory), str(self.play), '-e', json.dumps(variables)] + (['--check'] if check else []), capture_output=True, text=True, env=env, timeout=120)
        self.assertNotIn(PASSWORD, result.stdout + result.stderr)
        self.assertNotIn('synthetic-registry-only', result.stdout + result.stderr)
        self.assertNotIn('BEGIN PRIVATE KEY', result.stdout + result.stderr)
        self.assertNotIn((self.tls / 'gateway/tls.key').read_text(), result.stdout + result.stderr)
        return result

    def mutations(self):
        return [x for x in json.loads(self.state.read_text())['calls'] if x[0] in ('create', 'dry-run')]

    def test_limited_stage_keeps_delivery_guards_and_repeat(self):
        result = self.run_play(True, stage='local-logging-limited-pilot')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.run_play(True, stage='local-logging-limited-pilot')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('changed=0', result.stdout)

    def test_unrelated_stage_refuses_before_api_access(self):
        result = self.run_play(True, stage='local-nextcloud')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.state.read_text())['calls'], [])

    def test_default_and_check_modes_read_no_inputs_or_api(self):
        shutil.rmtree(self.private)
        for apply, check in [(False, False), (True, True)]:
            result = self.run_play(apply, check)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['calls'], [])

    def test_create_is_prevalidated_redacted_and_repeat_changes_nothing(self):
        result = self.run_play(True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([x[0] for x in self.mutations()], ['dry-run'] * 9 + ['create'] * 9)
        s = json.loads(self.state.read_text()); s['calls'] = []; self.state.write_text(json.dumps(s))
        result = self.run_play(True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.mutations(), [])
        self.assertIn('changed=0', result.stdout)

    def test_wrong_cluster_refuses_before_private_input_reads(self):
        s = json.loads(self.state.read_text()); s['uid'] = 'wrong'; self.state.write_text(json.dumps(s))
        shutil.rmtree(self.private)
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])
        self.assertEqual(len(json.loads(self.state.read_text())['calls']), 1)

    def test_unsafe_file_refuses_without_delivery(self):
        (self.private / 'password').chmod(0o644)
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_existing_unowned_credential_is_never_adopted_or_rotated(self):
        result = self.run_play(True); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        s = json.loads(self.state.read_text()); s['secrets']['monitoring/loki-query-auth']['metadata']['labels'] = {}; s['calls'] = []; self.state.write_text(json.dumps(s))
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_server_validation_failure_creates_nothing(self):
        s = json.loads(self.state.read_text()); s['reject_validation'] = True; self.state.write_text(json.dumps(s))
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertTrue(self.mutations())
        self.assertFalse(any(x[0] == 'create' for x in self.mutations()))

    def test_owned_credential_with_changed_password_is_never_rotated(self):
        result = self.run_play(True); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        s = json.loads(self.state.read_text()); s['calls'] = []; self.state.write_text(json.dumps(s))
        changed = 'cd34' * 24
        (self.private / 'password').write_text(changed)
        hashed = subprocess.run(['openssl', 'passwd', '-6', '-stdin'], input=changed, text=True, capture_output=True, check=True).stdout.strip()
        (self.private / 'htpasswd').write_text('fixture-admin:' + hashed)
        result = self.run_play(True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(changed, result.stdout + result.stderr)
        self.assertEqual(self.mutations(), [])

    def test_mismatched_htpasswd_refuses_before_api_delivery(self):
        (self.private / 'password').write_text('ef56' * 24)
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_wrong_ca_pin_refuses_before_api_delivery(self):
        self.fingerprint = '0' * 64
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_wrong_service_identity_refuses_before_api_delivery(self):
        shutil.copyfile(self.tls / 'gateway/tls.crt', self.tls / 'backend/tls.crt')
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_mismatched_private_key_refuses_before_api_delivery(self):
        shutil.copyfile(self.tls / 'gateway/tls.key', self.tls / 'backend/tls.key')
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_ambient_host_trust_cannot_override_the_pinned_ca(self):
        # Put the actual issuer in host-default trust, but pin a different CA.
        trust = self.folder / 'ambient-trust'; trust.mkdir()
        shutil.copyfile(self.ca, trust / 'issuer.pem')
        subprocess.run(['openssl', 'rehash', str(trust)], check=True, capture_output=True)
        other = self.folder / 'other-ca.crt'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(self.folder / 'other-ca.key'), '-out', str(other), '-days', '60', '-subj', '/CN=Different-synthetic-CA'], check=True, capture_output=True)
        other.chmod(0o600); self.ca = other
        self.fingerprint = subprocess.run(['openssl', 'x509', '-in', str(other), '-noout', '-fingerprint', '-sha256'], check=True, text=True, capture_output=True).stdout.strip().split('=')[1].replace(':', '').lower()
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_appended_unpinned_ca_is_not_accepted_as_a_bundle(self):
        issuer = self.ca.read_text()
        other = self.folder / 'bundle.crt'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(self.folder / 'bundle-ca.key'), '-out', str(other), '-days', '60', '-subj', '/CN=Pinned-but-unrelated-synthetic-CA'], check=True, capture_output=True)
        self.fingerprint = subprocess.run(['openssl', 'x509', '-in', str(other), '-noout', '-fingerprint', '-sha256'], check=True, text=True, capture_output=True).stdout.strip().split('=')[1].replace(':', '').lower()
        other.write_text(other.read_text() + issuer); other.chmod(0o600); self.ca = other
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])
