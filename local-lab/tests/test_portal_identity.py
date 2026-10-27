"""Offline platform contract tests. CEL execution is in portal-cel, not simulated here."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('portal_identity', ROOT/'local-lab/scripts/render-portal-identity.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PortalIdentityTests(unittest.TestCase):
    def setUp(self):
        self.contract = yaml.safe_load(module.CONTRACT.read_text())
        self.objects = module.resources(self.contract)

    def test_generated_outputs_match_and_never_include_secret_data(self):
        for name,content in module.outputs(self.contract).items():
            self.assertEqual((module.DIRECTORY/'generated'/name).read_text(),content)
        self.assertFalse(any(o['kind']=='Secret' for o in self.objects))
        self.assertFalse(any('secret' in client for client in module.identity_plan(self.contract)['clients']))

    def test_safe_default_has_no_manifest_or_mutation_output(self):
        result=subprocess.run(['python3',str(ROOT/'local-lab/scripts/render-portal-identity.py')],capture_output=True,text=True,check=True)
        plan=json.loads(result.stdout)
        self.assertEqual(plan['activation'],'disabled')
        self.assertIs(plan['writes'],False)
        self.assertIs(plan['networkCalls'],False)
        self.assertIs(plan['approvedImage'],False)

    def test_contract_refuses_activation_unknown_fields_and_invalid_identity(self):
        changes=[('activation','enabled'),('namespace','tenant-home-nextcloud'),('imageDigest','latest'),('tenantRevision','main'),('secret','never-allowed')]
        for key,value in changes:
            c=copy.deepcopy(self.contract);c[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):module.validate(c)
        for key,value in [('issuer','http://issuer.invalid/realms/perkforge'),('clientId','bad/client'),('clientSecret','forbidden')]:
            c=copy.deepcopy(self.contract);c['identity'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):module.validate(c)

    def test_inactive_fleet_and_immutable_platform_config(self):
        repo=next(o for o in self.objects if o['kind']=='GitRepo')['spec']
        self.assertIs(repo['paused'],True)
        self.assertEqual(repo['revision'],self.contract['tenantRevision'])
        self.assertEqual(set(repo['targets'][0]),{'name','clusterName'})
        cm=next(o for o in self.objects if o['kind']=='ConfigMap')
        self.assertIs(cm['immutable'],True)
        values=yaml.safe_load(cm['data']['values.yaml'])
        self.assertIs(values['enabled'],False)
        self.assertEqual(values['identity']['issuer'],self.contract['identity']['issuer'])
        self.assertEqual(values['identity']['existingSecret'],'portal-oidc')
        reference=yaml.safe_load(module.outputs(self.contract)['tenant-fleet-reference.yaml'])
        self.assertEqual(reference['helm']['valuesFrom'][0]['configMapKeyRef']['name'],cm['metadata']['name'])

    def test_rbac_only_workloads_and_named_config_read_no_secrets_or_identity_grants(self):
        role=next(o for o in self.objects if o['kind']=='Role')
        self.assertEqual({r for rule in role['rules'] for r in rule['resources']},{'deployments','services','configmaps'})
        config=next(r for r in role['rules'] if r['resources']==['configmaps'])
        self.assertEqual(config['verbs'],['get'])
        self.assertEqual(config['resourceNames'],['portal-platform-values'])
        self.assertFalse(any(o['kind']=='ClusterRoleBinding' for o in self.objects))
        for o in self.objects:
            if o['kind']=='ServiceAccount':self.assertIs(o['automountServiceAccountToken'],False)

    def test_admission_fails_closed_and_targets_namespace_without_tenant_labels(self):
        policies=[o for o in self.objects if o['kind']=='ValidatingAdmissionPolicy']
        self.assertEqual(len(policies),4)
        for p in policies:
            self.assertEqual(p['apiVersion'],'admissionregistration.k8s.io/v1')
            self.assertEqual(p['spec']['failurePolicy'],'Fail')
            if p['metadata']['name'] != 'portal-deployer-surface':
                self.assertEqual(p['spec']['matchConditions'][0]['expression'],'request.namespace == "tenant-home-portal"')
            self.assertNotIn('objectSelector',p['spec']['matchConstraints'])
        self.assertTrue(any(v['expression']=='false' for v in policies[0]['spec']['validations']))
        bindings=[o for o in self.objects if o['kind']=='ValidatingAdmissionPolicyBinding']
        self.assertEqual({b['spec']['policyName'] for b in bindings},{p['metadata']['name'] for p in policies})
        self.assertTrue(all(b['spec']['validationActions']==['Deny'] for b in bindings))

    def test_keycloak_plan_no_client_enablement_or_automatic_role_assignments(self):
        plan=module.identity_plan(self.contract)
        self.assertEqual(plan['realm'],'perkforge')
        self.assertEqual(plan['automaticRoleAssignments'],[])
        self.assertTrue(all(c['enabled'] is False for c in plan['clients']))
        client=plan['clients'][0]
        self.assertEqual(client['redirectUris'],['https://portal.local-lab.test/auth/callback'])
        self.assertFalse(client['serviceAccountsEnabled'])
        self.assertFalse(client['directAccessGrantsEnabled'])
        self.assertFalse(client['fullScopeAllowed'])
        self.assertEqual(client['attributes']['pkce.code.challenge.method'],'S256')
        mapper=next(m for m in client['protocolMappers'] if m['name']=='groups')
        self.assertEqual(mapper['config']['access.token.claim'],'true')
        self.assertEqual(plan['requiredClientScopeMapping']['roles'],['tenant-reader'])

    def test_no_new_active_paths_catalog_or_existing_security_output(self):
        for folder in ('local-lab/fleet','local-lab/tenant-config'):
            for path in (ROOT/folder).rglob('*.yaml'):
                self.assertNotIn('optional/portal',path.read_text())
                self.assertNotIn('portal-platform-values',path.read_text())
        self.assertFalse(any(p.name=='fleet.yaml' for p in module.DIRECTORY.rglob('*')))
