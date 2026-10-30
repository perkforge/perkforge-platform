"""A new platform-only root can omit tenant enrollment without changing packages."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import yaml
from fixtures.render_helpers import build
ROOT = Path(__file__).resolve().parents[2]

class OptionalEnrollmentTests(unittest.TestCase):
    def test_omitting_enrollment_preserves_all_other_root_objects(self):
        original = build(ROOT / 'clusters/local')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'bootstrap'
            shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns('tests', '__pycache__'))
            recipe = target / 'clusters/local/kustomization.yaml'
            data = yaml.safe_load(recipe.read_text())
            data['resources'].remove('../../enrollments/local')
            recipe.write_text(yaml.safe_dump(data, sort_keys=False))
            omitted = build(recipe.parent)
        selected = [o for o in original if o['metadata']['name'] != 'tenant-enrollments']
        canonical = lambda objects: sorted(json.dumps(o, sort_keys=True) for o in objects)
        self.assertEqual(canonical(omitted), canonical(selected))
        self.assertFalse(any('tenant-enrollment' in json.dumps(o) or 'enrollment-root-writer' in json.dumps(o)
                             for o in omitted))
        self.assertTrue(any(o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang' for o in omitted))
        bootstrap = (ROOT / 'configuration/ansible/bootstrap.yaml').read_text()
        self.assertNotIn('enrollment-prerequisites', bootstrap)
        prerequisites = yaml.safe_load((ROOT / 'configuration/ansible/enrollment-prerequisites.yaml').read_text())[0]
        self.assertFalse(prerequisites['vars']['enrollment_foundation_apply'])
