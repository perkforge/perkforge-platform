"""Package prerequisite ownership and ordering; offline renders only."""
import unittest
from pathlib import Path
import yaml
from fixtures.render_helpers import build
ROOT = Path(__file__).resolve().parents[2]

class PrerequisiteTests(unittest.TestCase):
    def test_packages_are_independent_and_combined_objects_have_one_definition(self):
        packages = {name: build(ROOT / 'configuration/packages' / name / 'prerequisites')
                    for name in ('bigbang', 'headlamp', 'keycloak')}
        for name, objects in packages.items():
            self.assertEqual({o['metadata']['name'] for o in objects if o['kind'] == 'Namespace'}, {name})
            recipe = yaml.safe_load((ROOT / 'configuration/packages' / name / 'prerequisites/kustomization.yaml').read_text())
            self.assertTrue(all('/' not in path for path in recipe['resources']))
        all_objects = sum(packages.values(), [])
        keys = [(o['apiVersion'], o['kind'], o['metadata'].get('namespace'), o['metadata']['name']) for o in all_objects]
        self.assertEqual(len(keys), len(set(keys)))
        for name in ('headlamp', 'keycloak'):
            selected = packages['bigbang'] + packages[name]
            roles = {(o['metadata']['namespace'], o['metadata']['name']) for o in selected if o['kind'] == 'Role'}
            for binding in (o for o in selected if o['kind'] == 'RoleBinding'):
                self.assertIn((binding['metadata']['namespace'], binding['roleRef']['name']), roles)
        self.assertFalse(any('headlamp' in o['metadata']['name'] for o in packages['keycloak']))

    def test_ansible_orders_common_before_only_selected_package(self):
        for package, playbook in [('headlamp', 'headlamp-prerequisites'), ('longhorn', 'longhorn-prerequisites'), ('rancher', 'rancher-prerequisites'), ('keycloak', 'keycloak-prerequisites')]:
            play = yaml.safe_load((ROOT / 'configuration/ansible' / (playbook + '.yaml')).read_text())[0]
            block = next(task['block'] for task in play['tasks'] if 'block' in task)
            apply = next(task for task in block if 'loop' in task and 'ansible.builtin.command' in task)
            if package != 'keycloak':
                self.assertEqual(apply['loop'], ['bigbang', package])
            else:
                from jinja2 import Environment
                paths=[Environment().from_string(item['path']).render(keycloak_storage_backend='longhorn') for item in apply['loop'][:2]]
                self.assertEqual(paths,['packages/bigbang/prerequisites','packages/keycloak/prerequisites-longhorn'])
                self.assertNotIn('headlamp', str(apply))
