"""Release permission regression and explicit envelope-integrity limitation.

Helm's storage envelope cannot attest the compressed release's Fleet identity.
No test contacts a cluster or performs a Helm operation. Live controller behavior
remains untested; source references and alternatives are in PORTAL-RELEASE-STORAGE.md.
"""
import base64
import copy
import gzip
import json
from pathlib import Path
import unittest

from portal_fleet_fixture import provisioned, render


def release_record(account):
    # Helm encodes JSON as gzip/base64; Kubernetes Secret serialization adds base64.
    # Only identity-relevant fields are needed for this synthetic counterexample.
    release = {'name': 'home-portal', 'namespace': 'tenant-home-portal', 'version': 1,
               'chart': {'metadata': {'annotations': {
                   'fleet.cattle.io/service-account': account,
                   'fleet.cattle.io/bundle-id': 'synthetic-bundle',
                   'fleet.cattle.io/agent-namespace': 'synthetic-agent-namespace'}}}}
    encoded = base64.b64encode(gzip.compress(json.dumps(release).encode(), mtime=0))
    return {'apiVersion': 'v1', 'kind': 'Secret',
            'metadata': {'name': 'sh.helm.release.v1.home-portal.v1',
                         'namespace': 'tenant-home-portal',
                         'labels': {'owner': 'helm', 'name': 'home-portal',
                                    'version': '1', 'status': 'deployed'}},
            'type': 'helm.sh/release.v1',
            'data': {'release': base64.b64encode(encoded).decode()}}


class ReleaseStorageBoundaryTests(unittest.TestCase):
    def test_envelope_checks_cannot_attest_stored_deployer_identity(self):
        expected = release_record('home-portal-deployer')
        altered = release_record('synthetic-other-deployer')
        envelope = lambda r: {k: v for k, v in r.items() if k != 'data'}
        self.assertEqual(envelope(expected), envelope(altered))
        self.assertEqual(set(expected['data']), set(altered['data']))
        for record, account in [(expected, 'home-portal-deployer'),
                                (altered, 'synthetic-other-deployer')]:
            decoded = json.loads(gzip.decompress(base64.b64decode(
                base64.b64decode(record['data']['release']))))
            self.assertEqual(decoded['chart']['metadata']['annotations'][
                'fleet.cattle.io/service-account'], account)
        # Checking the old envelope on UPDATE/DELETE does not resolve the ambiguity.
        self.assertEqual(envelope(copy.deepcopy(altered)), envelope(expected))

    def test_platform_grants_only_release_write_verbs(self):
        objects = render(provisioned())
        rules = [rule for o in objects if o['kind'] == 'Role'
                 for rule in o['rules'] if 'secrets' in rule['resources']]
        self.assertEqual(len(rules), 1)
        self.assertEqual(set(rules[0]['verbs']), {'create', 'update', 'delete'})

    def test_storage_opt_out_removes_secret_authority(self):
        home = provisioned()
        home['foundation']['repositories']['portal']['helmReleaseStorage'] = False
        for obj in render(home):
            if obj['kind'] == 'Role':
                self.assertFalse(any('secrets' in rule['resources'] for rule in obj['rules']))

    def test_catalog_does_not_activate_or_pin_local_image(self):
        import yaml
        root = Path(__file__).resolve().parents[2]
        home = yaml.safe_load((root/'local-lab/tenant-config/tenants/home.yaml').read_text())
        self.assertEqual(home['foundation']['lifecycle']['state'], 'disabled')
        self.assertIsNone(home['applications']['portal']['imageDigest'])
