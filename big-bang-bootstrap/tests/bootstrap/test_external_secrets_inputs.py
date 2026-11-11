"""Offline operator stages, synthetic credentials/CA and fake kubectl only."""
import base64
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ANSIBLE = ROOT / 'configuration/ansible'
spec = importlib.util.spec_from_file_location('eso_inputs', ANSIBLE / 'filter_plugins/external_secrets_inputs_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class InputValidation(unittest.TestCase):
    def test_exact_private_host_and_public_certificate_only(self):
        for value in ('10.23.45.67/32', '172.16.0.1/32', '192.168.1.1/32'):
            self.assertTrue(guard.provider_valid(value))
        for value in ('0.0.0.0/0', '10.0.0.0/8', '127.0.0.1/32', '169.254.1.1/32',
                      '100.64.0.1/32', '172.32.0.1/32', '8.8.8.8/32', '::1/128', '10.1.1.1', None):
            self.assertFalse(guard.provider_valid(value), value)
        pem = '-----BEGIN CERTIFICATE-----\nYWJjZA==\n-----END CERTIFICATE-----'
        self.assertTrue(guard.public_pem(pem))
        for value in (pem + '\nsecret-token', pem + '\n' + pem, pem.replace('CERTIFICATE', 'PRIVATE KEY')):
            self.assertFalse(guard.public_pem(value))

    def test_registry_entry_is_exactly_auth_only(self):
        auth = base64.b64encode(b"synthetic:password").decode()
        def secret(entry):
            return {"kind": "Secret", "type": "kubernetes.io/dockerconfigjson",
                    "data": {".dockerconfigjson": base64.b64encode(json.dumps(
                        {"auths": {"registry1.dso.mil": entry}}).encode()).decode()}}
        self.assertTrue(guard.registry_valid(secret({"auth": auth})))
        for field in ("username", "password", "email", "identitytoken", "registrytoken"):
            self.assertFalse(guard.registry_valid(secret({"auth": auth, field: "unexpected"})))
        self.assertFalse(guard.registry_valid(secret({})))

    def test_release_target_guards_and_activation_gate_are_present(self):
        play = yaml.safe_load((ANSIBLE / 'external-secrets-inputs.yaml').read_text())[0]
        for flag in ('registry', 'ca', 'network', 'activation'):
            self.assertIs(play['vars'][f'external_secrets_{flag}_apply'], False)
        text = yaml.safe_dump(play)
        for required in ('verify-release.yaml', '--porcelain', 'config_release.resolvedCommit',
                         'expected_cluster_uid', 'external_secrets_foundation_matches'):
            self.assertIn(required, text)
        self.assertTrue(play['tasks'][-1]['no_log'])
        self.assertIn('not ansible_check_mode', play['tasks'][-1]['when'])

    def test_activation_root_preserves_every_existing_object(self):
        from fixtures.render_helpers import build
        before = build(ROOT / 'clusters/local-external-secrets')
        after = build(ROOT / 'clusters/local-external-secrets-active')
        def key(obj):
            return obj['kind'], obj['metadata'].get('namespace'), obj['metadata']['name']
        old = {key(obj): obj for obj in before}
        new = {key(obj): obj for obj in after}
        self.assertEqual(old.keys(), new.keys())
        parent = ('HelmRelease', 'bigbang', 'bigbang')
        refs = new[parent]['spec']['valuesFrom']
        self.assertEqual([r['name'] for r in refs[-2:]],
                         ['external-secrets-network-values', 'external-secrets-activation-values'])
        self.assertTrue(all(r['optional'] is False for r in refs[-2:]))
        del refs[-2:]
        self.assertEqual(old, new)


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible required')
class InputStages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.playdir = self.directory / 'ansible'
        shutil.copytree(ANSIBLE / 'tasks', self.playdir / 'tasks')
        shutil.copytree(ANSIBLE / 'filter_plugins', self.playdir / 'filter_plugins')
        self.state = self.directory / 'state.json'
        self.state.write_text(json.dumps({'objects': {}, 'creates': 0, 'calls': 0}))
        self.password = 'synthetic-registry-secret-never-real'
        self.source = {'apiVersion': 'v1', 'kind': 'Secret', 'type': 'kubernetes.io/dockerconfigjson',
                       'data': {'.dockerconfigjson': base64.b64encode(json.dumps({'auths': {
                           'registry1.dso.mil': {'auth': base64.b64encode(('test:' + self.password).encode()).decode()}
                       }}).encode()).decode()}}
        self.cli = self.directory / 'kubectl'
        self.cli.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
p = Path(os.environ['ESO_TEST_STATE']); s = json.loads(p.read_text()); a = sys.argv[1:]
s['calls'] += 1
if a[0] == '-n':
 ns, op, kind, name = a[1:5]; assert op == 'get'
 if (ns, kind, name) == ('flux-system', 'secret', 'private-registry'):
  print(os.environ['ESO_TEST_SOURCE'])
 else:
  obj = s['objects'].get(ns + '/' + name)
  if obj: print(json.dumps(obj))
  elif '--ignore-not-found' not in a:
   p.write_text(json.dumps(s)); sys.exit(1)
elif a[0] == 'create':
 obj = json.load(sys.stdin); key = obj['metadata']['namespace'] + '/' + obj['metadata']['name']
 if '--dry-run=server' not in a:
  if key in s['objects'] or os.environ.get('ESO_TEST_RACE') == '1' or (int(os.environ.get('ESO_TEST_FAIL_AFTER', '-1')) >= 0 and s['creates'] >= int(os.environ['ESO_TEST_FAIL_AFTER'])):
   p.write_text(json.dumps(s)); sys.exit(1)
  s['objects'][key] = obj; s['creates'] += 1
 print('created')
else: raise SystemExit('Unexpected fixture operation')
p.write_text(json.dumps(s))
''')
        self.cli.chmod(0o700)
        self.ca = self.directory / 'public-ca.crt'
        subprocess.run(['openssl', 'req', '-new', '-x509', '-newkey', 'rsa:2048', '-noenc',
                        '-days', '3', '-subj', '/CN=Offline ESO CA', '-addext', 'basicConstraints=critical,CA:TRUE',
                        '-keyout', str(self.directory / 'synthetic.key'), '-out', str(self.ca)],
                       check=True, capture_output=True)
        fingerprint = subprocess.check_output(['openssl', 'x509', '-in', str(self.ca), '-noout', '-fingerprint', '-sha256'], text=True)
        self.provider = self.directory / 'provider-cidr'
        self.provider.write_text('10.23.45.67/32\n')
        self.provider.chmod(0o600)
        self.variables = {'eso_k': [str(self.cli)], 'external_secrets_registry_apply': True,
                          'external_secrets_ca_apply': True, 'external_secrets_network_apply': True,
                          'external_secrets_activation_apply': False,
                          'external_secrets_activation_prerequisites_approved': False,
                          'external_secrets_ca_file': str(self.ca),
                          'external_secrets_expected_ca_sha256': fingerprint.strip().split('=')[1].replace(':', '').lower(),
                          'external_secrets_provider_file': str(self.provider)}

    def run_stage(self, variables=None, race=False, fail_after=-1):
        play = self.playdir / 'fixture.yaml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': self.variables | (variables or {}), 'tasks': [
                {'ansible.builtin.include_tasks': 'tasks/external-secrets-inputs.yaml', 'no_log': True}]}]))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
            env=dict(os.environ, KUBECONFIG='/dev/null', ANSIBLE_LOCAL_TEMP=str(self.directory / 'tmp'),
                     ANSIBLE_REMOTE_TEMP=str(self.directory / 'remote'), ESO_TEST_STATE=str(self.state),
                     ESO_TEST_SOURCE=json.dumps(self.source), ESO_TEST_RACE='1' if race else '0', ESO_TEST_FAIL_AFTER=str(fail_after)),
            capture_output=True, text=True, timeout=90)
        self.assertNotIn(self.password, result.stdout + result.stderr)
        self.assertNotIn(self.source['data']['.dockerconfigjson'], result.stdout + result.stderr)
        self.assertNotIn('10.23.45.67', result.stdout + result.stderr)
        return result

    def state_data(self):
        return json.loads(self.state.read_text())

    def test_first_run_unchanged_repeat_and_separate_activation(self):
        result = self.run_stage()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        first = self.state_data()
        self.assertEqual(first['creates'], 3)
        self.assertNotIn('bigbang/external-secrets-activation-values', first['objects'])
        result = self.run_stage()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.state_data()['creates'], 3)
        self.assertEqual(self.state_data()['objects'], first['objects'])
        activation = {f'external_secrets_{stage}_apply': False for stage in ('registry', 'ca', 'network')}
        activation['external_secrets_activation_apply'] = True
        self.assertNotEqual(self.run_stage(activation).returncode, 0)
        self.assertEqual(self.state_data()['creates'], 3)
        activation['external_secrets_activation_prerequisites_approved'] = True
        result = self.run_stage(activation)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.state_data()['creates'], 4)
        self.assertEqual(self.run_stage(activation).returncode, 0)
        self.assertEqual(self.state_data()['creates'], 4)
        self.activation_objects = self.state_data()['objects']
        # Real pinned wrapper render: only the exact provider /32, no generic rule.
        chart = os.environ.get('ESO_CHART_SOURCE')
        if chart:
            from fixtures.render_helpers import helm
            values = yaml.safe_load((ROOT / 'configuration/external-secrets/runtime/native-values.yaml').read_text())['addons']['externalSecrets']['values']
            network = yaml.safe_load(self.activation_objects['bigbang/external-secrets-network-values']['data']['values.yaml'])['addons']['externalSecrets']['values']
            rendered = helm(Path(chart) / 'chart', 'external-secrets', 'external-secrets', [yaml.safe_dump(values), yaml.safe_dump(network)])
            policies = [o for o in rendered if o['kind'] == 'NetworkPolicy']
            self.assertIn('10.23.45.67/32', yaml.safe_dump(policies))
            self.assertNotIn('0.0.0.0/0', yaml.safe_dump(policies))
            if os.environ.get('PREFLIGHT_SOURCES_DIR'):
                from fixtures.render_helpers import build, ordered_values
                umbrella = Path(os.environ['PREFLIGHT_SOURCES_DIR']) / 'bigbang/chart'
                def parent_render(root_name):
                    objects = build(ROOT / 'clusters' / root_name)
                    objects += list(self.activation_objects.values())
                    objects.append({'kind': 'ConfigMap', 'metadata': {'name': 'velero-runtime-values'},
                                    'data': {'velero.yaml': (ROOT / 'configuration/packages/velero/candidate-values.yaml').read_text()}})
                    parent = next(o for o in objects if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
                    return helm(umbrella, 'bigbang', 'bigbang', ordered_values(objects, parent))
                before = parent_render('local-external-secrets')
                after = parent_render('local-external-secrets-active')
                controller = next(o for o in after if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'external-secrets')
                self.assertIs(controller['spec']['suspend'], False)
                def unrelated(objects):
                    return [o for o in objects if o['metadata']['name'] not in
                            ('external-secrets', 'bigbang-external-secrets-values')]
                self.assertEqual(unrelated(before), unrelated(after))
                from fixtures.render_helpers import child_values
                effective = helm(Path(chart) / "chart", "external-secrets", "external-secrets", child_values(after, "external-secrets"))
                provider = [o for o in effective if o["kind"] == "NetworkPolicy" and
                            o["metadata"]["name"] == "allow-egress-from-external-secrets-to-openbao-approved"]
                self.assertEqual(len(provider), 1)
                self.assertEqual(provider[0]["metadata"]["namespace"], "external-secrets")
                self.assertEqual(provider[0]["spec"], {
                    "podSelector": {"matchLabels": {"app.kubernetes.io/name": "external-secrets"}},
                    "policyTypes": ["Egress"], "egress": [{
                        "to": [{"ipBlock": {"cidr": "10.23.45.67/32"}}],
                        "ports": [{"protocol": "TCP", "port": 443}]}]})
                self.assertFalse(any(o["kind"] == "NetworkPolicy" and "secrets-api-subnets" in o["metadata"]["name"] for o in effective))

    def test_partial_creation_is_retained_and_retry_only_completes_missing_inputs(self):
        activation = {"external_secrets_activation_apply": True,
                      "external_secrets_activation_prerequisites_approved": True}
        result = self.run_stage(activation, fail_after=2)
        self.assertNotEqual(result.returncode, 0)
        partial = self.state_data()
        self.assertEqual(partial["creates"], 2)
        self.assertEqual(set(partial["objects"]), {"external-secrets/private-registry", "external-secrets/openbao-ca"})
        result = self.run_stage(activation)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        completed = self.state_data()
        self.assertEqual(completed["creates"], 4)
        for key, value in partial["objects"].items():
            self.assertEqual(completed["objects"][key], value)
        self.assertEqual(set(completed["objects"]) - set(partial["objects"]),
                         {"bigbang/external-secrets-network-values", "bigbang/external-secrets-activation-values"})
        self.assertEqual(self.run_stage(activation).returncode, 0)
        self.assertEqual(self.state_data()["creates"], 4)
        self.assertEqual(self.state_data()["objects"], completed["objects"])

    def test_existing_unowned_drift_and_race_never_overwrite(self):
        result = self.run_stage()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        original = self.state_data()
        for mutation in ('owner', 'data', 'immutable', 'ownerReferences'):
            state = copy.deepcopy(original)
            obj = state['objects']['external-secrets/private-registry']
            if mutation == 'owner': obj['metadata']['labels'] = {}
            elif mutation == 'data': obj['data'] = {'.dockerconfigjson': 'bad'}
            elif mutation == 'immutable': obj['immutable'] = False
            else: obj['metadata']['ownerReferences'] = [{'uid': 'other-owner'}]
            self.state.write_text(json.dumps(state))
            self.assertNotEqual(self.run_stage().returncode, 0)
            self.assertEqual(self.state_data()['objects'], state['objects'])
            self.assertEqual(self.state_data()['creates'], 3)
        self.state.write_text(json.dumps({'objects': {}, 'creates': 0, 'calls': 0}))
        self.assertNotEqual(self.run_stage(race=True).returncode, 0)
        self.assertEqual(self.state_data()['creates'], 0)

    def test_bad_inputs_and_missing_prerequisites_never_activate(self):
        activation = {f'external_secrets_{stage}_apply': False for stage in ('registry', 'ca', 'network')}
        activation.update(external_secrets_activation_apply=True, external_secrets_activation_prerequisites_approved=True)
        self.assertNotEqual(self.run_stage(activation).returncode, 0)
        self.assertEqual(self.state_data()['creates'], 0)
        for value in ('0.0.0.0/0', '10.0.0.0/8', '127.0.0.1/32'):
            self.provider.write_text(value)
            self.assertNotEqual(self.run_stage().returncode, 0)
            self.assertEqual(self.state_data()['creates'], 0)
        self.provider.write_text('10.23.45.67/32')
        self.assertNotEqual(self.run_stage({'external_secrets_expected_ca_sha256': '0' * 64}).returncode, 0)
        self.assertEqual(self.state_data()['creates'], 0)
        self.ca.write_text(self.ca.read_text() + '\nSECRET-TOKEN')
        self.assertNotEqual(self.run_stage().returncode, 0)
        self.assertEqual(self.state_data()['creates'], 0)

    def test_registry_scope_and_no_access_defaults(self):
        self.source['data']['other'] = 'unexpected'
        self.assertNotEqual(self.run_stage().returncode, 0)
        self.assertEqual(self.state_data()['creates'], 0)
        inventory = self.directory / 'inventory.yaml'
        inventory.write_text('all:\n  children:\n    bootstrap_clusters:\n      hosts:\n        local:\n          ansible_connection: local\n')
        fake = self.directory / 'bin'; fake.mkdir()
        for tool in ('kubectl', 'gh', 'git'):
            script = fake / tool
            script.write_text('#!/bin/sh\necho UNEXPECTED_ACCESS >&2\nexit 99\n'); script.chmod(0o700)
        for extra in ([], ['--check', '-e', '{"external_secrets_registry_apply":true,"external_secrets_ca_apply":true,"external_secrets_network_apply":true,"external_secrets_activation_apply":true}']):
            result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(ANSIBLE / 'external-secrets-inputs.yaml'), *extra],
                env=dict(os.environ, PATH=str(fake) + ':' + os.environ['PATH'], ANSIBLE_LOCAL_TEMP=str(self.directory / 'local')),
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('UNEXPECTED_ACCESS', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
