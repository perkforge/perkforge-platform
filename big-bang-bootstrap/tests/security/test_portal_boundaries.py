"""Local proposal contracts, separate from verification of published dependencies."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml
from fixtures.render_helpers import build
from security.portal_admission_cases import fixtures

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.environ.get('PORTAL_ENROLLMENT_CHECKOUT') and os.environ.get('PORTAL_APP_CHECKOUT'),
                     'explicit coordinated proposal checkouts required')
class PortalTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.enrollment = Path(os.environ['PORTAL_ENROLLMENT_CHECKOUT'])
        cls.app = Path(os.environ['PORTAL_APP_CHECKOUT'])
        cls.foundation = build(cls.enrollment / 'tenants/portal/foundation')

    def test_authoritative_root_keeps_identity_first_and_generic_enrollment_paused(self):
        objects = build(ROOT / 'clusters/local')
        parent = [o for o in objects if o['metadata']['name'] == 'tenant-enrollments']
        self.assertEqual(parent, [])
        retained = build(ROOT / 'enrollments/local')
        parent = [o for o in retained if o['metadata']['name'] == 'tenant-enrollments']
        self.assertEqual({o['kind'] for o in parent}, {'GitRepository','Kustomization'})
        self.assertTrue(all(o['spec']['suspend'] is True for o in parent))
        self.assertNotIn('secretRef', next(o for o in parent if o['kind'] == 'GitRepository')['spec'])
        self.assertFalse((ROOT / 'stages').exists())
        self.assertEqual(sum(o['kind'] == 'HelmRelease' for o in objects), 1)
        for path in (ROOT / 'enrollments/prerequisites').glob('*.yaml'):
            self.assertNotIn('portal',path.read_text().lower())

    def test_three_repository_reconciler_namespaces_and_runtime_are_separate(self):
        enrolled = build(self.enrollment / 'clusters/local')
        self.assertTrue(all(o['metadata']['namespace']=='tenant-portal-config' for o in enrolled))
        child = next(o for o in enrolled if o['kind']=='Kustomization')
        self.assertEqual(child['spec']['targetNamespace'], 'tenant-portal-config')
        self.assertEqual(child['spec']['serviceAccountName'], 'portal-reconciler')
        self.assertEqual(child['spec']['path'], './gitops/clusters/local')
        self.assertNotIn('secretRef', next(o for o in enrolled if o['kind']=='GitRepository')['spec'])
        release = next(o for o in build(self.app/'gitops/clusters/local') if o['kind']=='HelmRelease')
        self.assertEqual(release['spec']['serviceAccountName'], 'portal-deployer')
        self.assertEqual(release['spec']['targetNamespace'], 'tenant-portal')
        self.assertEqual(release['spec']['storageNamespace'], 'tenant-portal-release')
        accounts = {(o['metadata']['name'],o['metadata']['namespace']) for o in self.foundation if o['kind']=='ServiceAccount'}
        self.assertEqual(accounts, {('portal-reconciler','tenant-portal-config'),('portal-deployer','tenant-portal-config'),('portal-runtime','tenant-portal')})
        self.assertTrue(all(not o['automountServiceAccountToken'] for o in self.foundation if o['kind']=='ServiceAccount'))

    def test_workload_cannot_mount_control_identities_or_gain_rbac_and_storage(self):
        self.assertFalse(any(o['kind'] in ['ClusterRole','ClusterRoleBinding','Secret','Deployment','PersistentVolumeClaim'] for o in self.foundation))
        bindings = [o for o in self.foundation if o['kind']=='RoleBinding']
        self.assertFalse(any(s['name']=='portal-runtime' for o in bindings for s in o['subjects']))
        for role in [o for o in self.foundation if o['kind']=='Role']:
            for rule in role['rules']:
                self.assertNotIn('*', rule['apiGroups']+rule['resources']+rule['verbs'])
                self.assertFalse(set(rule['resources']) & {'roles','rolebindings','serviceaccounts','namespaces','pods/exec','pods/portforward'})
        controls = [o for o in self.foundation if o['kind']=='ResourceQuota' and o['metadata']['namespace']!='tenant-portal']
        self.assertEqual(len(controls),2)
        self.assertTrue(all(o['spec']['hard']['pods']=='0' for o in controls))

    def test_admission_is_native_fail_closed_and_published_image_matches_app(self):
        policies = [o for o in self.foundation if o['kind']=='ValidatingAdmissionPolicy']
        bindings = [o for o in self.foundation if o['kind']=='ValidatingAdmissionPolicyBinding']
        self.assertEqual(len(policies),4)
        self.assertEqual(len(bindings),4)
        self.assertTrue(all(o['spec']['failurePolicy']=='Fail' for o in policies))
        self.assertTrue(all(o['spec']['validationActions']==['Deny'] for o in bindings))
        bound = next(o for o in bindings if o['spec'].get('paramRef'))
        self.assertEqual(bound['spec']['paramRef']['parameterNotFoundAction'],'Deny')
        contract = next(o for o in self.foundation if o['kind']=='ConfigMap')
        self.assertEqual(contract['data']['image'], 'ghcr.io/perkforge/perkforge-portal@sha256:ae13143108562e9753eab40650cfcef4b53d8336e733adc6a94dbccabc0a2616')
        self.assertGreaterEqual(len(fixtures()['cases']),30)

    def test_keycloak_client_claims_remain_separate_from_api_oidc_and_no_membership_writes(self):
        client = yaml.safe_load((self.enrollment/'tenants/portal/identity/client.yaml').read_text())
        self.assertEqual(client['clientId'],'portal-local')
        self.assertFalse(client['fullScopeAllowed'])
        for field in ['publicClient','implicitFlowEnabled','directAccessGrantsEnabled','serviceAccountsEnabled']:
            self.assertFalse(client[field])
        self.assertEqual(client['redirectUris'],['https://portal-local-il2.local-lab.test/auth/callback'])
        self.assertEqual(client['webOrigins'],['https://portal-local-il2.local-lab.test'])
        self.assertEqual(client['attributes']['pkce.code.challenge.method'],'S256')
        mappers = {m['name']:m['config'] for m in client['protocolMappers']}
        self.assertEqual(mappers['portal-groups']['full.path'],'true')
        self.assertEqual(mappers['portal-groups']['access.token.claim'],'true')
        self.assertEqual(mappers['portal-audience']['included.client.audience'],'portal-local')
        self.assertEqual(mappers['portal-api-role']['usermodel.clientRoleMapping.clientId'],'portal-local')
        for path in (self.enrollment/'ansible').glob('*.yaml'):
            for text in ['delete/reimport','/users/', '/members/']:
                self.assertNotIn(text,path.read_text())

    def test_approved_ansible_gate_has_no_default_or_check_mode_side_effects(self):
        for name,flag in [('prepare-local-portal','portal_foundation_apply'),('configure-portal-identity','portal_identity_apply'),('deliver-portal-inputs','portal_inputs_apply')]:
            play = self.enrollment/'ansible'/f'{name}.yaml'
            self.assertFalse(yaml.safe_load(play.read_text())[0]['vars'][flag])
            for enabled in [False,True]:
                with tempfile.TemporaryDirectory() as d:
                    result=subprocess.run(['ansible-playbook','-i','localhost,',str(play),'--check','-e',f'{flag}={str(enabled).lower()}'],
                        capture_output=True,text=True,env={**os.environ,'ANSIBLE_LOCAL_TEMP':d+'/local','ANSIBLE_REMOTE_TEMP':d+'/remote'})
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('changed=0',result.stdout)

    def test_portal_render_budget_adds_only_one_small_workload_and_service(self):
        cases=fixtures()['cases'];deployment=next(c['object'] for c in cases if c['name']=='approved portal chart')
        pod=deployment['spec']['template']['spec'];container=pod['containers'][0]
        self.assertEqual(container['resources'],{'requests':{'cpu':'25m','memory':'64Mi'},'limits':{'cpu':'250m','memory':'192Mi'}})
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['serviceAccountName'],'portal-runtime')
        self.assertEqual(pod['nodeSelector'],{'kubernetes.io/hostname':'cks-worker'})
        self.assertEqual(deployment['spec']['strategy']['type'],'Recreate')
        for repo,relative in [(self.enrollment,'clusters/dev/kustomization.yaml'),(self.app,'gitops/clusters/dev/values.yaml')]:
            baseline=subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+relative],text=True)
            self.assertEqual((repo/relative).read_text(),baseline)
