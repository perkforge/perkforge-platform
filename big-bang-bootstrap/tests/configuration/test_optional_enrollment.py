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
from fixtures.selection import release_for
ROOT = Path(__file__).resolve().parents[2]

class OptionalEnrollmentTests(unittest.TestCase):
    def test_nextcloud_stage_preserves_packages_and_selects_only_its_enrollment_path(self):
        baseline=build(ROOT/'clusters/local-gitlab-runner')
        proposed=build(ROOT/'clusters/local-nextcloud')
        existing=[x for x in proposed if x['metadata']['name']!='tenant-enrollments']
        canonical=lambda xs:sorted(json.dumps(x,sort_keys=True) for x in xs)
        self.assertEqual(canonical(baseline),canonical(existing))
        enrolled=[x for x in proposed if x['metadata']['name']=='tenant-enrollments']
        self.assertEqual({x['kind'] for x in enrolled},{'GitRepository','Kustomization'})
        parent=next(x for x in enrolled if x['kind']=='Kustomization')
        source=next(x for x in enrolled if x['kind']=='GitRepository')
        evidence=json.loads((ROOT.parent/'release-evidence.json').read_text())['dependencies']['nextcloud-enrollment']
        release_for(source,evidence)
        self.assertEqual(parent['spec']['path'],'./clusters/local-nextcloud')
        self.assertEqual(parent['spec']['serviceAccountName'],'tenant-enrollment-admin')
        self.assertFalse(parent['spec']['prune'])
        self.assertTrue(all(not x['spec']['suspend'] for x in enrolled))

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

    def test_selected_stage_is_checked_without_enabling_the_default_root(self):
        for identity,accepted in [('tenant-enrollment-admin',True),('unreviewed-admin',False)]:
            with self.subTest(identity=identity), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); repo=root/'repo'
                shutil.copytree(ROOT,repo/'big-bang-bootstrap',ignore=shutil.ignore_patterns('tests','__pycache__'))
                stage=repo/'big-bang-bootstrap/clusters/local-nextcloud';stage.mkdir(exist_ok=True)
                (stage/'kustomization.yaml').write_text(yaml.safe_dump({'resources':['../local','../../enrollments/local-nextcloud']}))
                fixture=root/'objects.yaml'
                fixture.write_text(yaml.safe_dump_all([
                    {'apiVersion':'source.toolkit.fluxcd.io/v1','kind':'GitRepository','metadata':{'name':'tenant-enrollments','namespace':'flux-system'},
                     'spec':{'url':'https://github.com/perkforge/perkforge-platform-tenants.git','ref':{'tag':'v1.2.3'}}},
                    {'apiVersion':'kustomize.toolkit.fluxcd.io/v1','kind':'Kustomization','metadata':{'name':'tenant-enrollments','namespace':'flux-system'},
                     'spec':{'serviceAccountName':identity,'sourceRef':{'kind':'GitRepository','name':'tenant-enrollments'},'path':'./clusters/local-nextcloud','prune':False}}
                ]))
                tools=root/'bin';tools.mkdir();marker=root/'api-called'
                tool=tools/'kubectl'
                tool.write_text('#!/bin/sh\nif [ "$1" = kustomize ]; then cat "'+str(fixture)+'"; else touch "'+str(marker)+'"; exit 98; fi\n')
                tool.chmod(0o700)
                result=subprocess.run(['ansible-playbook','-i',str(repo/'big-bang-bootstrap/configuration/ansible/inventory.yaml'),
                    str(repo/'big-bang-bootstrap/configuration/ansible/enrollment-prerequisites.yaml'),'-e','enrollment_foundation_apply=true',
                    '-e','gitops_path=./big-bang-bootstrap/clusters/local-nextcloud'],capture_output=True,text=True,timeout=20,
                    env={**os.environ,'PATH':str(tools)+':'+os.environ['PATH'],'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote')})
                self.assertNotEqual(result.returncode,0) # Deliberately no published release input supplied.
                self.assertEqual('Require a version and reviewed non-secret release evidence' in result.stdout,accepted,result.stdout+result.stderr)
                self.assertFalse(marker.exists())
