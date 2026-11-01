"""Nonsecret Ansible review render and explicit authorization MODEL, not live proof."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
REVIEW=ROOT/'configuration/authorization'
class AuthorizationReview(unittest.TestCase):
 def run_play(self,directory,extra=None,check=False,play=None):
  env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(Path(directory)/'ansible-local'),'ANSIBLE_REMOTE_TEMP':str(Path(directory)/'ansible-remote'),'ANSIBLE_NOCOLOR':'1'}
  args=['ansible-playbook','-i','localhost,',str(play or REVIEW/'preview.yaml')]
  if extra:args+=['-e',json.dumps(extra)]
  if check:args+=['--check']
  return subprocess.run(args,env=env,capture_output=True,text=True,timeout=40)
 def test_safe_defaults_check_and_activation_refusal(self):
  with tempfile.TemporaryDirectory() as d:
   for extra,check in [({},False),({},True),({'authorization_render':True},True)]:
    p=self.run_play(d,extra,check);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('changed=0',p.stdout)
   for extra in [{'authorization_apply':True},{'authorization_integrations':{'headlamp':{'enabled':True}}},{'authorization_tenants':['a/b']},{'authorization_tenants':['a','a']}]:
    p=self.run_play(d,extra);self.assertNotEqual(p.returncode,0)
 def test_actual_ansible_render_has_disabled_clients_and_tenant_specific_grants(self):
  with tempfile.TemporaryDirectory() as d:
   output=Path(d)/'review';extra={'authorization_render':True,'authorization_output_directory':str(output),'authorization_tenants':['a','b']}
   p=self.run_play(d,extra);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
   self.assertEqual(output.stat().st_mode&0o777,0o700)
   self.assertTrue(all(f.stat().st_mode&0o777==0o600 for f in output.iterdir()))
   realm=yaml.safe_load((output/'realm.yaml').read_text());self.assertEqual(realm['realm'],'perkforge');self.assertEqual(realm['displayName'],'PerkForge')
   self.assertNotIn('users',realm);self.assertNotIn('roles',realm)
   self.assertEqual({c['clientId'] for c in realm['clients']},{'headlamp-local','rancher','openbao'})
   for c in realm['clients']:
    self.assertFalse(c['enabled']);self.assertFalse(c['fullScopeAllowed']);self.assertFalse(c['serviceAccountsEnabled']);self.assertFalse(c['directAccessGrantsEnabled']);self.assertNotIn('secret',c)
    self.assertEqual(c['protocolMappers'][0]['config']['full.path'],'true')
   objects=list(yaml.safe_load_all((output/'kubernetes.yaml').read_text()))
   self.assertEqual(len([o for o in objects if o['kind']=='ClusterRoleBinding']),1)
   def permitted(group,ns,api,resource,verb):
    for b in objects:
     if not b['kind'].endswith('RoleBinding') or not any(s['name']==group for s in b['subjects']):continue
     if b['kind']=='ClusterRoleBinding' and b['roleRef']['name']=='cluster-admin':return True
     if b['metadata']['namespace']!=ns:continue
     role=next(o for o in objects if o['kind']=='Role' and o['metadata']['namespace']==ns and o['metadata']['name']==b['roleRef']['name'])
     if any(api in rule['apiGroups'] and resource in rule['resources'] and verb in rule['verbs'] for rule in role['rules']):return True
    return False
   self.assertTrue(permitted('oidc:/platform/admins','','','nodes','delete'))
   for tenant,other in [('a','b'),('b','a')]:
    admin=f'oidc:/tenants/{tenant}/admins';dev=f'oidc:/tenants/{tenant}/developers';ns='tenant-'+tenant
    for who in [admin,dev]:
     self.assertTrue(permitted(who,ns,'apps','deployments','patch'))
     self.assertFalse(permitted(who,'tenant-'+other,'apps','deployments','patch'))
     for api,res,verb in [('', 'nodes','get'),('rbac.authorization.k8s.io','rolebindings','create'),('rbac.authorization.k8s.io','clusterroles','bind'),('','serviceaccounts/token','create'),('','namespaces','patch')]:self.assertFalse(permitted(who,ns,api,res,verb))
    self.assertTrue(permitted(admin,ns,'','secrets','get'));self.assertTrue(permitted(admin,ns,'','pods/exec','create'))
    for res,verb in [('secrets','get'),('serviceaccounts','create'),('pods/exec','create'),('pods/portforward','create')]:self.assertFalse(permitted(dev,ns,'',res,verb))
   self.assertFalse(permitted('oidc:/tenants/a/admins-extra','tenant-a','apps','deployments','patch'))
   self.assertFalse(permitted('oidc:/tenants','tenant-a','apps','deployments','patch'))
   bao=yaml.safe_load((output/'openbao-roles.yaml').read_text())
   for tenant in ['a','b']:
    role=bao['roles'][f'tenant-{tenant}-admin'];self.assertEqual(role['bound_claims'],{'groups':[f'/tenants/{tenant}/admins']})
    policy=bao['policies'][f'proposed-tenant-{tenant}-admin'];self.assertIn(f'tenants/data/{tenant}/*',policy);self.assertNotIn('sys/',policy)
   self.assertTrue((REVIEW/'desired.yaml').is_file())
   p=self.run_play(d,extra);self.assertNotEqual(p.returncode,0) # Never overwrite evidence.
 def test_empty_tenants_and_existing_api_workflow_remain_inactive(self):
  with tempfile.TemporaryDirectory() as d:
   output=Path(d)/'empty';p=self.run_play(d,{'authorization_render':True,'authorization_output_directory':str(output)})
   self.assertEqual(p.returncode,0,p.stdout+p.stderr);realm=yaml.safe_load((output/'realm.yaml').read_text());self.assertEqual(realm['groups'][1]['subGroups'],[])
   play=ROOT/'configuration/ansible/platform-config/configure.yaml'
   for extra,check in [({},False),({},True),({'platform_api_apply':True},True)]:
    p=self.run_play(d,extra,check,play);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('changed=0',p.stdout)
