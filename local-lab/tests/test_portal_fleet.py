"""Native Fleet lifecycle and regression evidence; none of this runs in deployment."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import yaml
from portal_fleet_fixture import BUNDLE, ROOT, home_values, portal_values, provisioned, render, run_fleet

sys.path.insert(0, str(ROOT / 'local-lab/scripts'))
from tenant_catalog import load_catalog
spec = importlib.util.spec_from_file_location('legacy_foundation', ROOT / 'local-lab/scripts/render-tenant-foundation.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def review_transition(before, after):
    previous = before.get('applications', {}).get('portal', {}).get('lifecycle', {}).get('state', 'disabled')
    desired = after.get('applications', {}).get('portal', {}).get('lifecycle', {}).get('state', 'disabled')
    if previous in ('active', 'paused') and desired not in ('active', 'paused'):
        raise ValueError('Provisioned portal must remain active/paused; removal or decommission needs separate review')


def review_budget(home):
    # Reuse existing quantity/budget checks as TESTS, not as a configuration prerequisite.
    catalog = load_catalog(BUNDLE / 'tenants.yaml')
    reviewed = copy.deepcopy(home)
    app = portal_values(home)
    if app['lifecycle']['state'] != 'disabled':
        reviewed['environments'].append({'name': 'portal-review', 'namespace': app['namespace'],
                                        'allocation': app['resources']['allocation']})
    catalog['tenants'] = [reviewed if t['id'] == 'home' else t for t in catalog['tenants']]
    legacy.validate_catalog(catalog)


def existing_controls(objects):
    # Fleet adds ownership metadata; comparing configuration must retain everything else.
    result = []
    for item in copy.deepcopy(objects):
        if item['kind'] in ('Namespace', 'ResourceQuota', 'LimitRange'):
            continue
        metadata = item['metadata']
        for key in ('annotations', 'labels'):
            if key in metadata:
                metadata[key] = {k: v for k, v in metadata[key].items() if not k.startswith('objectset.rio.cattle.io/')}
                if not metadata[key]:
                    del metadata[key]
        if item['kind'] == 'ConfigMap':
            item['data']['values.yaml'] = yaml.safe_load(item['data']['values.yaml'])
        result.append(item)
    return sorted(result, key=lambda o: (o['apiVersion'], o['kind'], o['metadata'].get('namespace', ''), o['metadata']['name']))


class PortalFleetTests(unittest.TestCase):
    def test_existing_tenants_remain_byte_identical(self):
        files = legacy.render_files(load_catalog(BUNDLE / 'tenants.yaml'))
        self.assertEqual(len(files), 16)
        for name, text in files.items():
            self.assertEqual((legacy.DEFAULT_OUTPUT / name).read_text(), text)
        self.assertNotIn('home-portal', legacy.render(load_catalog(BUNDLE / 'tenants.yaml')))

    def test_active_and_paused_preserve_all_identities_and_controls(self):
        before = json.loads((Path(__file__).parent / 'fixtures/portal/native-controls-baseline.json').read_text())
        identity_sets = []
        for state in ('active', 'paused'):
            objects = render(provisioned(state))
            identities = {(o['apiVersion'], o['kind'], o['metadata'].get('namespace'), o['metadata']['name']) for o in objects}
            self.assertEqual(len(identities), len(objects))
            identity_sets.append(identities)
            self.assertEqual(next(o for o in objects if o['kind'] == 'GitRepo')['spec']['paused'], state == 'paused')
            controls = existing_controls(objects)
            self.assertEqual(len(controls), 19)
            digest = hashlib.sha256(json.dumps(controls, sort_keys=True).encode()).hexdigest()
            self.assertEqual(digest, before[state], 'Reviewed identity/security controls drifted')
        self.assertEqual(identity_sets[0], identity_sets[1])

    def test_namespace_has_platform_owner_and_inherited_restrictions(self):
        objects = render(provisioned())
        namespace = next(o for o in objects if o['kind'] == 'Namespace')
        self.assertEqual(namespace['metadata']['name'], 'tenant-home-portal')
        self.assertEqual(namespace['metadata']['annotations']['field.cattle.io/projectId'], 'local:p-home-local')
        self.assertEqual(namespace['metadata']['labels']['platform.perkforge.io/tenant'], 'home')
        self.assertEqual(namespace['metadata']['labels']['pod-security.kubernetes.io/enforce'], 'restricted')
        self.assertEqual(namespace['metadata']['labels']['pod-security.kubernetes.io/enforce-version'], 'v1.36')
        self.assertEqual(len([o for o in objects if o['kind'] == 'NetworkPolicy' and o['metadata']['name'] == 'default-deny']), 1)
        self.assertFalse(any(o['kind'] == 'Project' for o in objects))

    def test_duplicate_namespace_and_disabled_allocation_are_rejected(self):
        home = provisioned()
        home['environments'].append({'namespace': 'tenant-home-portal'})
        self.assertNotEqual(run_fleet(home).returncode, 0)
        home = provisioned()
        home['applications']['portal']['lifecycle']['state'] = 'disabled'
        self.assertNotEqual(run_fleet(home).returncode, 0)

    def test_budget_review_includes_existing_home_and_new_portal(self):
        review_budget(home_values())
        home = provisioned()
        review_budget(home)
        home['resources']['budget']['pods'] = '6'
        with self.assertRaisesRegex(ValueError, 'exceed tenant budget'):
            review_budget(home)

    def test_transition_review_forbids_deletion_or_disabled_after_provisioning(self):
        for previous in ('active', 'paused'):
            before = provisioned(previous)
            for after in (home_values(), {k: v for k, v in home_values().items() if k != 'applications'}):
                with self.assertRaisesRegex(ValueError, 'separate review'):
                    review_transition(before, after)
            for following in ('active', 'paused'):
                review_transition(before, provisioned(following))

    def test_current_git_candidate_against_review_base(self):
        review_budget(home_values())
        shared = yaml.safe_load((BUNDLE / 'values.yaml').read_text())
        self.assertEqual(shared['applications']['portal']['lifecycle']['state'], 'disabled')
        # CI supplies the exact base SHA and fetches history. No live inventory is inferred.
        base = os.environ.get('PORTAL_REVIEW_BASE')
        if base:
            previous = subprocess.check_output(['git', 'show', f'{base}:local-lab/tenant-config/tenants/home.yaml'], cwd=ROOT, text=True)
            review_transition(yaml.safe_load(previous), home_values())

    def test_wrong_cluster_does_not_receive_home_configuration(self):
        # An unmatched Fleet target must not accidentally render the local Home values.
        result = run_fleet(provisioned(), cluster='unrelated')
        self.assertTrue(result.returncode != 0 or not result.stdout.strip())
