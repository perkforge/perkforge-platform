"""Catalog lifecycle and no-prune regression tests; all writes are temporary/offline."""
import copy
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'local-lab/scripts'))
from tenant_catalog import load_catalog
import portal_application
spec=importlib.util.spec_from_file_location('foundation',ROOT/'local-lab/scripts/render-tenant-foundation.py')
foundation=importlib.util.module_from_spec(spec);spec.loader.exec_module(foundation)

class PortalCatalogLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.catalog=load_catalog(ROOT/'local-lab/tenant-config/tenants.yaml')

    def home(self,catalog=None):
        return next(t for t in (catalog or self.catalog)['tenants'] if t['id']=='home')

    def provisioned(self,state):
        c=copy.deepcopy(self.catalog);home=self.home(c)
        home['applications']['portal']['lifecycle']['state']=state
        home['applications']['portal']['imageDigest']='sha256:'+'a'*64
        env=copy.deepcopy(home['environments'][0]);env['name']='portal-local-vm';env['namespace']='tenant-home-portal'
        home['environments'].append(env)
        home['resources']['budget']={'pods':'12','requests.cpu':'1200m','requests.memory':'2Gi','limits.cpu':'4','limits.memory':'4Gi','persistentvolumeclaims':'6','requests.storage':'12Gi','services':'10'}
        return c

    def test_current_catalog_is_byte_identical_to_legacy_tenant_output(self):
        before=copy.deepcopy(self.catalog);self.home(before).pop('applications')
        self.assertEqual(foundation.render_files(before),foundation.render_files(self.catalog))
        files=foundation.render_files(self.catalog)
        self.assertEqual(len(files),16)
        for path,text in files.items():
            self.assertEqual((foundation.DEFAULT_OUTPUT/path).read_text(),text)
        self.assertNotIn('home-portal',foundation.render(self.catalog))

    def test_portal_is_home_application_inheriting_groups_and_cluster(self):
        self.assertEqual({t['id'] for t in self.catalog['tenants']},{'home','tenant-alpha','tenant-bravo'})
        contract=portal_application.contract_for(self.catalog)
        self.assertEqual(contract['identity']['groups'],list(self.home()['identity']['groups'].values()))
        self.assertEqual(contract['kubernetesVersion'],'1.36')
        self.assertNotIn('groups',self.home()['applications']['portal']['identity'])
        c=copy.deepcopy(self.catalog);self.home(c)['applications']['portal']['identity']['groups']=[]
        with self.assertRaises(ValueError):foundation.render(c)

    def test_provisioned_requires_image_and_explicit_budgeted_environment(self):
        c=copy.deepcopy(self.catalog);app=self.home(c)['applications']['portal'];app['lifecycle']['state']='active'
        with self.assertRaisesRegex(ValueError,'image digest'):foundation.render(c)
        app['imageDigest']='sha256:'+'a'*64
        with self.assertRaisesRegex(ValueError,'budgeted'):foundation.render(c)
        c=self.provisioned('active');self.home(c)['resources']['budget']['pods']='6'
        with self.assertRaisesRegex(ValueError,'exceed tenant budget'):foundation.render(c)

    def test_active_and_paused_keep_same_resource_identities(self):
        active=list(yaml.safe_load_all(foundation.render(self.provisioned('active'))))
        paused=list(yaml.safe_load_all(foundation.render(self.provisioned('paused'))))
        identity=lambda o:(o['apiVersion'],o['kind'],o['metadata'].get('namespace'),o['metadata']['name'])
        self.assertEqual({identity(o) for o in active},{identity(o) for o in paused})
        self.assertEqual(len(active),len({identity(o) for o in active}), 'No duplicate namespace policy ownership')
        self.assertEqual(len([o for o in active if o['kind']=='Project']),3)
        ns=next(o for o in active if o['kind']=='Namespace' and o['metadata']['name']=='tenant-home-portal')
        self.assertEqual(ns['metadata']['labels']['platform.perkforge.io/tenant'],'home')
        self.assertEqual(ns['metadata']['labels']['platform.perkforge.io/application'],'portal')
        self.assertEqual(ns['metadata']['labels']['pod-security.kubernetes.io/enforce'],'restricted')
        for objects,pause in [(active,False),(paused,True)]:
            repo=next(o for o in objects if o['kind']=='GitRepo');self.assertEqual(repo['spec']['paused'],pause)
            cm=next(o for o in objects if o['kind']=='ConfigMap');self.assertIs(yaml.safe_load(cm['data']['values.yaml'])['enabled'],True)
        self.assertEqual(len([o for o in paused if o['kind']=='ValidatingAdmissionPolicy']),4)

    def test_disabled_with_existing_allocation_is_rejected(self):
        c=self.provisioned('paused');self.home(c)['applications']['portal']['lifecycle']['state']='disabled'
        with self.assertRaisesRegex(ValueError,'unprovisioned'):foundation.render(c)
        self.home(c)['applications']['portal']['lifecycle']['state']='decommissioned'
        with self.assertRaisesRegex(ValueError,'decommission'):foundation.render(c)

    def test_writer_refuses_disabled_or_removed_application_without_touching_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);output=root/'generated';catalog=root/'catalog.yaml'
            previous=foundation.render_files(self.provisioned('paused'))
            for name,text in previous.items():
                path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
            command=['python3',str(ROOT/'local-lab/scripts/render-tenant-foundation.py'),'--catalog',str(catalog),'--output',str(output),'--write']
            for removed in [False,True]:
                desired=copy.deepcopy(self.catalog)
                if removed:self.home(desired).pop('applications')
                catalog.write_text(yaml.safe_dump(desired))
                result=subprocess.run(command,capture_output=True,text=True)
                self.assertEqual(result.returncode,2)
                self.assertIn('Refusing to prune',result.stderr)
                self.assertEqual({p.relative_to(output):p.read_text() for p in output.rglob('*.yaml')},previous)

    def test_combined_output_writer_also_refuses_pruning(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'combined.yaml';before=foundation.render(self.provisioned('paused'));output.write_text(before)
            result=subprocess.run(['python3',str(ROOT/'local-lab/scripts/render-tenant-foundation.py'),'--output',str(output),'--write'],capture_output=True,text=True)
            self.assertEqual(result.returncode,2);self.assertEqual(output.read_text(),before)

    def test_preview_must_stay_outside_active_fleet_paths(self):
        result=subprocess.run(['python3',str(ROOT/'local-lab/scripts/render-tenant-foundation.py'),'--preview-application','home/portal','--output',str(foundation.DEFAULT_OUTPUT),'--check'],capture_output=True,text=True)
        # Default output selects the safe dedicated preview directory, not Fleet.
        self.assertEqual(result.returncode,0)
        result=subprocess.run(['python3',str(ROOT/'local-lab/scripts/render-tenant-foundation.py'),'--preview-application','home/portal','--output',str(foundation.DEFAULT_OUTPUT/'unsafe'),'--write'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
