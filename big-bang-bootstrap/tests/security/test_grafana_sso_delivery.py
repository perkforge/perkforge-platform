"""Offline execution of the delivery playbook against a recording kubectl fixture."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
PLAY = ROOT / 'big-bang-bootstrap/configuration/authorization/sso/grafana/deliver-inputs.yaml'

CLI = '''#!/usr/bin/python3
import json, os, sys
from pathlib import Path
p=Path(os.environ['GF_FIXTURE_STATE']);s=json.loads(p.read_text());a=sys.argv[1:]
s['calls'].append(a)
def out(value):
 p.write_text(json.dumps(s))
 print(json.dumps(value) if not isinstance(value,str) else value)
 sys.exit(0)
def fail():
 p.write_text(json.dumps(s));sys.exit(1)
if 'config' in a:
 out({'clusters':[{'cluster':{'server':s['api'],'insecure-skip-tls-verify':s.get('insecure',False)}}]})
if 'get' in a:
 i=a.index('get');kind,name=a[i+1:i+3]
 if kind=='namespace':out(s['uids'][name])
 key=kind+'/'+name
 if key not in s['objects']:
  if '--ignore-not-found' in a:out('')
  fail()
 out(s['objects'][key])
if 'create' in a:
 obj=json.load(sys.stdin);key=obj['kind']+'/'+obj['metadata']['name']
 if key in s['objects']:fail()
 if "--dry-run=server" in a:
  if s.get("reject_dry_run") and obj["kind"]=="ConfigMap":fail()
  out("dry-run accepted")
 if s.get('fail_ca') and obj['kind']=='ConfigMap':fail()
 s['writes'].append(key);s['objects'][key]=obj;out('created')
fail()
'''

class GrafanaDelivery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.cli = self.d / 'kubectl'
        self.cli.write_text(CLI)
        self.cli.chmod(0o700)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '2',
                        '-subj', '/CN=fixture-CA', '-addext', 'basicConstraints=critical,CA:TRUE',
                        '-keyout', str(self.d / 'key'), '-out', str(self.d / 'ca')], check=True, capture_output=True)
        for name, value in [('config', 'fixture-kubeconfig'), ('secret', 'fixture-existing-grafana-secret')]:
            (self.d / name).write_text(value)
            (self.d / name).chmod(0o600)
        self.state = self.d / 'state.json'
        self.state.write_text(json.dumps(dict(calls=[], writes=[], objects={}, api='https://cluster.example.test:6443',
                                             uids={'kube-system': '11111111-1111-1111-1111-111111111111',
                                                   'monitoring': '22222222-2222-2222-2222-222222222222'})))
        self.v = dict(grafana_delivery_run=True, grafana_delivery_approval='grafana-sso-input-delivery-v1',
                      grafana_kubectl=str(self.cli), grafana_kubeconfig=str(self.d / 'config'),
                      grafana_context='fixture', grafana_expected_api='https://cluster.example.test:6443',
                      grafana_expected_cluster_uid='11111111-1111-1111-1111-111111111111',
                      grafana_expected_monitoring_uid='22222222-2222-2222-2222-222222222222',
                      grafana_client_secret_file=str(self.d / 'secret'), grafana_ca_file=str(self.d / 'ca'),
                      grafana_expected_ca_sha256=hashlib.sha256((self.d / 'ca').read_bytes()).hexdigest())

    def state_value(self):
        return json.loads(self.state.read_text())

    def update(self, **changes):
        self.state.write_text(json.dumps(dict(self.state_value(), **changes)))

    def run_play(self, extra=None, check=False, success=True):
        p = subprocess.run(['ansible-playbook', str(PLAY), '-e', json.dumps(dict(self.v, **(extra or {})))] +
                           (['--check'] if check else []), capture_output=True, text=True, timeout=90,
                           env=dict(os.environ, GF_FIXTURE_STATE=str(self.state), KUBECONFIG='/dev/null',
                                    ANSIBLE_LOCAL_TEMP=str(self.d / 'local'), ANSIBLE_REMOTE_TEMP=str(self.d / 'remote')))
        self.assertEqual(p.returncode == 0, success, p.stdout + p.stderr)
        self.assertNotIn('fixture-existing-grafana-secret', p.stdout + p.stderr)
        self.assertNotIn('Zml4dHVyZS1leGlzdGluZy1ncmFmYW5hLXNlY3JldA==', p.stdout + p.stderr)
        return p

    def test_default_check_and_missing_approval_are_noncontacting(self):
        self.run_play(dict(grafana_delivery_run=False, grafana_client_secret_file='/missing'))
        self.run_play(dict(grafana_client_secret_file='/missing'), check=True)
        self.run_play(dict(grafana_delivery_approval='UNAPPROVED'), success=False)
        self.assertEqual(self.state_value()['calls'], [])

    def test_exact_create_and_no_change_repeat(self):
        self.run_play()
        s = self.state_value()
        self.assertEqual(s['writes'], ['Secret/grafana-oidc-client', 'ConfigMap/grafana-identity-ca'])
        self.assertTrue(all(v['immutable'] for v in s['objects'].values()))
        self.assertIn('changed=0', self.run_play().stdout)
        self.assertEqual(self.state_value()['writes'], s['writes'])
        for args in self.state_value()['calls']:
            self.assertNotIn('fixture-existing-grafana-secret', ' '.join(args))
            self.assertFalse(any(v in args for v in ['apply', 'patch', 'delete', 'list']))
            if 'get' in args and 'namespace' not in args:
                self.assertIn(args[args.index('get') + 2], ['grafana-oidc-client', 'grafana-identity-ca'])

    def test_partial_creation_resumes_without_rotating_secret(self):
        self.update(fail_ca=True)
        self.run_play(success=False)
        self.assertEqual(self.state_value()['writes'], ['Secret/grafana-oidc-client'])
        self.update(fail_ca=False)
        self.run_play()
        self.assertEqual(self.state_value()['writes'], ['Secret/grafana-oidc-client', 'ConfigMap/grafana-identity-ca'])

    def test_collision_and_rotation_are_refused_before_writes(self):
        self.run_play()
        original = self.state_value()
        for kind in ['Secret/grafana-oidc-client', 'ConfigMap/grafana-identity-ca']:
            for field, value in [('immutable', False), ('data', {'foreign': 'value'})]:
                s = json.loads(json.dumps(original))
                s['objects'][kind][field] = value
                self.state.write_text(json.dumps(s))
                self.run_play(success=False)
                self.assertEqual(self.state_value()['writes'], original['writes'])
        self.state.write_text(json.dumps(original))
        (self.d / 'secret').write_text('replacement-grafana-secret-is-not-authorized')
        self.run_play(success=False)
        self.assertEqual(self.state_value()['writes'], original['writes'])

    def test_dry_run_rejection_and_terminating_object_never_persist(self):
        self.update(reject_dry_run=True)
        self.run_play(success=False)
        self.assertEqual(self.state_value()["writes"], [])
        self.assertEqual(self.state_value()["objects"], {})
        self.update(reject_dry_run=False)
        self.run_play()
        s = self.state_value()
        s["objects"]["Secret/grafana-oidc-client"]["metadata"]["deletionTimestamp"] = "2026-11-07T00:00:00Z"
        self.state.write_text(json.dumps(s))
        self.run_play(success=False)
        self.assertEqual(self.state_value()["writes"], s["writes"])

    def test_cluster_namespace_and_tls_drift_refused(self):
        for changes in [dict(api='https://foreign.test'), dict(insecure=True),
                        dict(uids={'kube-system': 'foreign', 'monitoring': 'foreign'})]:
            original = self.state_value()
            self.update(**changes)
            self.run_play(success=False)
            self.assertEqual(self.state_value()['writes'], [])
            self.state.write_text(json.dumps(original))

    def test_bad_ca_mode_and_parent_refused_before_api(self):
        self.run_play(dict(grafana_expected_ca_sha256='0' * 64), success=False)
        self.d.chmod(0o755)
        self.run_play(success=False)
        self.d.chmod(0o700)
        (self.d / 'secret').chmod(0o644)
        self.run_play(success=False)
        self.assertEqual(self.state_value()['calls'], [])
        (self.d / 'secret').chmod(0o600)
        (self.d / 'ca').write_text((self.d / 'key').read_text())
        self.run_play(dict(grafana_expected_ca_sha256=hashlib.sha256((self.d / 'ca').read_bytes()).hexdigest()), success=False)
        self.assertEqual(self.state_value()['calls'], [])
