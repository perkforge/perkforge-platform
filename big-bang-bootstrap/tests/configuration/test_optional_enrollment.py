"""The authoritative local root excludes enrollment until explicit opt-in."""
import json
import os
import subprocess
from pathlib import Path
import shutil
import tempfile
import unittest
import yaml
from fixtures.render_helpers import build
ROOT = Path(__file__).resolve().parents[2]

class OptionalEnrollmentTests(unittest.TestCase):
    def test_default_excludes_enrollment_and_explicit_opt_in_preserves_packages(self):
        original = build(ROOT / 'clusters/local')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'bootstrap'
            shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns('tests', '__pycache__'))
            recipe = target / 'clusters/local/kustomization.yaml'
            data = yaml.safe_load(recipe.read_text())
            self.assertNotIn('../../enrollments/local', data['resources'])
            data['resources'].append('../../enrollments/local')
            recipe.write_text(yaml.safe_dump(data, sort_keys=False))
            enabled = build(recipe.parent)
        selected = [o for o in enabled if o['metadata']['name'] != 'tenant-enrollments']
        enrollment = [o for o in enabled if o['metadata']['name'] == 'tenant-enrollments']
        self.assertEqual({o['kind'] for o in enrollment}, {'GitRepository', 'Kustomization'})
        self.assertTrue(all(o['spec']['suspend'] for o in enrollment))
        canonical = lambda objects: sorted(json.dumps(o, sort_keys=True) for o in objects)
        self.assertEqual(canonical(original), canonical(selected))
        self.assertFalse(any('tenant-enrollment' in json.dumps(o) or 'enrollment-root-writer' in json.dumps(o)
                             for o in original))
        self.assertTrue(any(o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang' for o in original))
        bootstrap = (ROOT / 'configuration/ansible/bootstrap.yaml').read_text()
        self.assertNotIn('enrollment-prerequisites', bootstrap)
        prerequisites = yaml.safe_load((ROOT / 'configuration/ansible/enrollment-prerequisites.yaml').read_text())[0]
        self.assertFalse(prerequisites['vars']['enrollment_foundation_apply'])

    def test_enrollment_apply_refuses_unselected_root_before_external_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); marker = root / 'called'
            for name in ['kubectl', 'gh', 'git']:
                tool = root / name
                tool.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 99\n')
                tool.chmod(0o700)
            result = subprocess.run(['ansible-playbook', '-i', str(ROOT / 'configuration/ansible/inventory.yaml'),
                                     str(ROOT / 'configuration/ansible/enrollment-prerequisites.yaml'),
                                     '-e', 'enrollment_foundation_apply=true'], capture_output=True, text=True, timeout=20,
                                    env={**os.environ, 'PATH': directory+':'+os.environ['PATH'],
                                         'ANSIBLE_LOCAL_TEMP': directory+'/local', 'ANSIBLE_REMOTE_TEMP': directory+'/remote'})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Tenant enrollment is disabled', result.stdout)
            self.assertFalse(marker.exists())
