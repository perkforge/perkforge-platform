"""Offline checks; synthetic API fixtures never target a live cluster."""
import json
from collections import Counter
from copy import deepcopy
import os, subprocess, tempfile, unittest, base64, uuid
from pathlib import Path
import yaml
from fixtures.render_helpers import build, child_values, helm, ordered_values, release_name
from fixtures.resource_inventory import inventory
from fixtures.lookup_server import lookup_server, secret_allowed
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT
EX = ROOT
CLUSTER = ROOT / 'clusters/local'
STAGE = ROOT / 'configuration/identity'
from fixtures.package_context import HeadlampFixture

class PackageBootstrapTests(HeadlampFixture):
    def test_foundation_defaults_and_wrong_target_never_call_api(self):
        for target, extra, expected in [('local', {}, 0), ('local', {'deployment_environment': 'dev'}, 2),
            ('local', {'headlamp_registry_apply': True}, 2),
            ('local', {'foundation_apply': True, 'config_tag': 'main'}, 2)]:
            with self.subTest(target=target, extra=extra), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                marker = path / 'api-called'
                for tool in ['kubectl', 'gh']:
                    stub = path / tool
                    stub.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 99\n')
                    stub.chmod(0o700)
                result = subprocess.run(['ansible-playbook', '-i', str(EXAMPLES / 'configuration/ansible/inventory.yaml'),
                    str(EXAMPLES / 'configuration/ansible/headlamp-foundation.yaml'), '--limit', target,
                    '-e', json.dumps(extra)], text=True, capture_output=True,
                    env={**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                         'KUBECONFIG': '/dev/null', 'ANSIBLE_LOCAL_TEMP': directory + '/ansible',
                         'ANSIBLE_REMOTE_TEMP': directory + '/remote'})
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                self.assertFalse(marker.exists())
                if expected == 0:
                    self.assertIn('changed=0', result.stdout)

    def test_named_root_seed_is_public_and_paused(self):
        with tempfile.TemporaryDirectory() as directory:
            template = EXAMPLES / 'configuration/ansible/seed.yaml.j2'
            args = json.dumps({'msg': "{{ lookup('ansible.builtin.template', '" + str(template) + "') }}"})
            output = subprocess.check_output(['ansible', 'local', '-i', str(EXAMPLES / 'configuration/ansible/inventory.yaml'),
                '-m', 'ansible.builtin.debug', '-a', args, '-e', 'config_source_secret='],
                text=True, env={**os.environ, 'ANSIBLE_LOCAL_TEMP': directory, 'ANSIBLE_NOCOLOR': '1'})
            response, _ = json.JSONDecoder().raw_decode(output[output.index('{'):])
            seed = list(yaml.safe_load_all(response['msg']))
            source = next(o for o in seed if o['kind'] == 'GitRepository')
            root = next(o for o in seed if o['kind'] == 'Kustomization')
            self.assertNotIn('secretRef', source['spec'])
            self.assertTrue(source['spec']['suspend'])
            self.assertTrue(root['spec']['suspend'])
            self.assertFalse(root['spec']['prune'])
            self.assertEqual(root['spec']['path'], './big-bang-bootstrap/clusters/local')
            self.assertEqual(root['spec']['serviceAccountName'], 'platform-reconciler')

    def test_registry_delivery_is_private_stdin_and_rejects_insecure_file(self):
        for mode, expected in [(0o600, 0), (0o644, 2)]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                credential = path / 'fixture-only'
                value = 'fixture-' + uuid.uuid4().hex
                credential.write_text(value)
                credential.chmod(mode)
                payload = path / 'stdin.json'
                arguments = path / 'arguments.txt'
                stub = path / 'kubectl'
                stub.write_text('#!/bin/sh\ncat > "' + str(payload) + '"\nprintf "%s\\n" "$@" > "' + str(arguments) + '"\n')
                stub.chmod(0o700)
                play = path / 'fixture.yaml'
                play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                    'gather_facts': False, 'vars': {'registry_username': 'fixture-user',
                    'registry_credential_file': str(credential), 'target_kubeconfig': '/dev/null',
                    'target_context': 'fixture'}, 'tasks': [{'ansible.builtin.include_tasks':
                    str(EXAMPLES / 'configuration/ansible/headlamp-registry.yaml')}]}]))
                result = subprocess.run(['ansible-playbook', str(play)], text=True, capture_output=True,
                    env={**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                         'ANSIBLE_LOCAL_TEMP': directory + '/ansible',
                         'ANSIBLE_REMOTE_TEMP': directory + '/remote'})
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                self.assertNotIn(value, result.stdout + result.stderr)
                if expected:
                    self.assertFalse(payload.exists())
                    continue
                self.assertNotIn(value, arguments.read_text())
                secret = json.loads(payload.read_text())
                self.assertEqual(secret['metadata'], {'name': 'private-registry', 'namespace': 'headlamp'})
                self.assertEqual(secret['type'], 'kubernetes.io/dockerconfigjson')
                auths = json.loads(secret['stringData']['.dockerconfigjson'])['auths']
                self.assertEqual(set(auths), {'registry1.dso.mil'})
                decoded = base64.b64decode(auths['registry1.dso.mil']['auth']).decode()
                self.assertEqual(decoded, 'fixture-user:' + value)
                self.assertNotIn(auths['registry1.dso.mil']['auth'], result.stdout + result.stderr)
