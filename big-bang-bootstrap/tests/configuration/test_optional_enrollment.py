"""The authoritative local root excludes enrollment until explicit opt-in."""
import json
import copy
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
    def test_active_portal_release_preserves_both_notification_mounts(self):
        objects = build(ROOT / 'clusters/local-platform-alerts')
        source = next(o for o in objects if o['kind'] == 'GitRepository' and o['metadata']['name'] == 'tenant-enrollments')
        evidence = json.loads((ROOT.parent / 'release-evidence.json').read_text())['dependencies']['active-portal-enrollment']
        release_for(source, evidence)
        parent = next(o for o in objects if o['kind'] == 'Kustomization' and o['metadata']['name'] == 'tenant-enrollments')
        self.assertEqual(parent['spec']['path'], './clusters/local-nextcloud-portal')
        self.assertFalse(parent['spec']['prune'])
        umbrella = next(o for o in objects if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
        mounts = [v['name'] for v in umbrella['spec']['valuesFrom']]
        self.assertIn('grafana-ntfy-values', mounts)
        self.assertIn('grafana-platform-alerts-values', mounts)

    def test_nextcloud_stage_preserves_packages_except_explicit_operator_watch(self):
        baseline=build(ROOT/'clusters/local-gitlab-runner')
        proposed=build(ROOT/'clusters/local-nextcloud')
        existing=[x for x in proposed if x['metadata']['name'] not in {'tenant-enrollments', 'nextcloud-oidc-issuer'}]
        baseline=copy.deepcopy(baseline)
        expected=next(x for x in baseline if x['kind']=='HelmRelease' and x['metadata']['name']=='platform-cnpg')
        watch='gitlab,tenant-home-nextcloud'
        expected['spec']['values']={'config':{'data':{'WATCH_NAMESPACE':watch}}}
        patch=expected['spec']['postRenderers'][0]['kustomize']['patches'][0]
        parsed=yaml.safe_load(patch['patch'])
        parsed['spec']['template']['spec']['containers'][0]['env'][0]['value']=watch
        patch['patch']=yaml.safe_dump(parsed)
        def canonical(xs):
            xs=copy.deepcopy(xs)
            for x in xs:
                for renderer in x.get('spec',{}).get('postRenderers',[]):
                    for patch in renderer.get('kustomize',{}).get('patches',[]):
                        patch['patch']=yaml.safe_load(patch['patch'])
            return sorted(json.dumps(x,sort_keys=True) for x in xs)
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

    def test_metrics_and_velero_stages_keep_nextcloud_and_portal_selections_separate(self):
        evidence = json.loads((ROOT.parent / 'release-evidence.json').read_text())['dependencies']
        for stage in ['local-metrics-limited-pilot-ui', 'local-velero']:
            with self.subTest(stage=stage):
                objects = build(ROOT / 'clusters' / stage)
                enrolled = [obj for obj in objects if obj['metadata']['name'] == 'tenant-enrollments']
                self.assertEqual({obj['kind'] for obj in enrolled}, {'GitRepository', 'Kustomization'})
                source = next(obj for obj in enrolled if obj['kind'] == 'GitRepository')
                parent = next(obj for obj in enrolled if obj['kind'] == 'Kustomization')
                release_for(source, evidence['nextcloud-enrollment'])
                self.assertEqual(parent['spec']['path'], './clusters/local-nextcloud')
                self.assertEqual(parent['spec']['serviceAccountName'], 'tenant-enrollment-admin')
                self.assertFalse(parent['spec']['prune'])
                self.assertTrue(all(not obj['spec']['suspend'] for obj in enrolled))
        portal = build(ROOT / 'enrollments/local')
        portal_source = next(obj for obj in portal if obj['kind'] == 'GitRepository')
        portal_parent = next(obj for obj in portal if obj['kind'] == 'Kustomization')
        release_for(portal_source, evidence['enrollment'])
        self.assertEqual(portal_source['spec']['ref'], {'tag': 'v1.0.0'})
        self.assertEqual(portal_parent['spec']['path'], './clusters/local')
        self.assertTrue(all(obj['spec']['suspend'] for obj in portal))

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
