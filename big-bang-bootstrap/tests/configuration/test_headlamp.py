"""Offline checks; synthetic API fixtures never target a live cluster."""
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

class HeadlampConfigurationTests(HeadlampFixture):
    def test_explicit_identity_fixture_selects_only_reviewed_packages(self):
        self.assertEqual(sum(o['kind'] == 'HelmRelease' for o in self.root), 1)
        self.assertFalse(self.parent['spec']['suspend'])
        self.assertEqual({o['metadata']['name'] for o in self.outer if o['kind'] == 'HelmRelease'}, {'headlamp', 'keycloak'})
        self.assertEqual({o['metadata']['name'] for o in self.outer if o['kind'] == 'GitRepository'}, {'headlamp', 'keycloak'})
        self.assertFalse(any(o['metadata']['name'] == 'openbao' for o in self.outer))
        self.assertEqual(Counter(o['kind'] for o in self.child), {'ServiceAccount': 1, 'Service': 1, 'Deployment': 1})
        self.assertEqual(self.child_release['metadata']['name'], 'headlamp')
        self.assertEqual({o['metadata']['namespace'] for o in self.child}, {'headlamp'})
        self.assertEqual(Counter(o['kind'] for o in self.foundation), {'Namespace': 2, 'ServiceAccount': 3, 'Role': 4, 'RoleBinding': 4})
        self.assertEqual({o['metadata']['name'] for o in self.foundation if o['kind'] == 'Namespace'}, {'bigbang','headlamp'})
    def test_actual_pull_wiring_limits_private_service_and_bounded_retries(self):
        deployment = next(o for o in self.child if o['kind'] == 'Deployment')
        pod = deployment['spec']['template']['spec']
        self.assertEqual(pod['imagePullSecrets'], [{'name': 'private-registry'}])
        self.assertEqual(pod['nodeSelector']['kubernetes.io/hostname'], 'REPLACE_WITH_WORKER_NODE')
        self.assertEqual(pod['containers'][0]['resources'],
                         {'requests': {'cpu': '100m', 'memory': '128Mi'},
                          'limits': {'cpu': '500m', 'memory': '256Mi'}})
        self.assertFalse(any('unsafe' in arg for c in pod['containers'] for arg in c.get('args', [])))
        self.assertNotIn('hostNetwork', pod)
        self.assertTrue(all('hostPort' not in port for c in pod['containers'] for port in c.get('ports', [])))
        service = next(o for o in self.child if o['kind'] == 'Service')
        self.assertEqual(service['spec']['type'], 'ClusterIP')
        report = inventory(self.child)
        self.assertEqual(report['claims'], [])
        self.assertEqual(report['steadyRequestsMi'], 128)
        self.assertEqual(report['steadyLimitsMi'], 256)
        self.assertEqual(report['images'], ['registry1.dso.mil/ironbank/opensource/headlamp-k8s/headlamp:v0.45.0'])
        self.assertEqual(self.parent['spec']['serviceAccountName'], 'platform-reconciler')
        self.assertEqual(self.child_release['spec']['serviceAccountName'], 'headlamp-installer')
        self.assertEqual(self.child_release['spec']['storageNamespace'], 'bigbang')
        for release in [self.parent, self.child_release]:
            self.assertFalse(release['spec']['install']['createNamespace'])
            for action in ['install', 'upgrade']:
                self.assertEqual(release['spec'][action]['remediation'],
                                 {'retries': 0, 'remediateLastFailure': False})

    def test_pinned_crd_supports_scoped_installer_fields(self):
        objects = yaml.safe_load_all((self.sources / 'bigbang/base/flux/gotk-components.yaml').read_text())
        crd = next(o for o in objects if o and o['kind'] == 'CustomResourceDefinition'
                   and o['metadata']['name'] == 'helmreleases.helm.toolkit.fluxcd.io')
        spec = next(v for v in crd['spec']['versions'] if v['name'] == 'v2')['schema']['openAPIV3Schema']['properties']['spec']['properties']
        for field in ['postRenderers', 'storageNamespace', 'serviceAccountName', 'install', 'upgrade']:
            self.assertIn(field, spec)
        for action in ['install', 'upgrade']:
            fields = spec[action]['properties']['remediation']['properties']
            self.assertIn('remediateLastFailure', fields)
            self.assertIn('retries', fields)


    def test_unselected_custom_package_does_not_create_wrapper_source(self):
        self.assertFalse(any(o['metadata']['name'] == 'bigbang-wrapper' for o in self.outer))
        self.assertNotIn('openbao', yaml.safe_load((ROOT / 'clusters/local/values.yaml').read_text()).get('packages', {}))
