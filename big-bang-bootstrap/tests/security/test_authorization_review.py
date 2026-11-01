"""Nonsecret Ansible review render and explicit authorization MODEL, not live proof."""
import json,os,subprocess,tempfile,unittest,re,fnmatch
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
   for extra in [{'authorization_apply':True},{'authorization_platform_viewer_group':'/platform/admins'},{'authorization_integrations':{'headlamp':{'enabled':True}}},{'authorization_tenants':['a/b']},{'authorization_tenants':['a','a']}]:
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
   self.assertEqual(len([o for o in objects if o['kind']=='ClusterRoleBinding']),2)
   def permitted(group,ns,api,resource,verb):
    for b in objects:
     if not b['kind'].endswith('RoleBinding') or not any(s['name']==group for s in b['subjects']):continue
     if b['kind']=='ClusterRoleBinding' and b['roleRef']['name']=='cluster-admin':return True
     if b['kind']=='ClusterRoleBinding':
      role=next(o for o in objects if o['kind']=='ClusterRole' and o['metadata']['name']==b['roleRef']['name'])
     else:
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
    self.assertTrue(permitted(dev,ns,'','secrets','get'));self.assertTrue(permitted(dev,ns,'','secrets','list'))
    for verb in ['create','update','patch','delete']:self.assertFalse(permitted(dev,ns,'','secrets',verb))
    viewer=f'oidc:/tenants/{tenant}/viewers'
    self.assertTrue(permitted(viewer,ns,'apps','deployments','get'))
    self.assertFalse(permitted(viewer,'tenant-'+other,'apps','deployments','get'))
    for api,res,verb in [('apps','deployments','patch'),('','secrets','get'),('','secrets','list'),('','pods/exec','create')]:self.assertFalse(permitted(viewer,ns,api,res,verb))
    for res,verb in [('serviceaccounts','create'),('pods/exec','create'),('pods/portforward','create')]:self.assertFalse(permitted(dev,ns,'',res,verb))
   multi=['oidc:/tenants/a/admins','oidc:/tenants/b/viewers']
   self.assertTrue(any(permitted(g,'tenant-a','apps','deployments','patch') for g in multi))
   self.assertTrue(any(permitted(g,'tenant-b','apps','deployments','get') for g in multi))
   self.assertFalse(any(permitted(g,'tenant-b','apps','deployments','patch') for g in multi))
   self.assertFalse(any(permitted(g,'tenant-c','apps','deployments','get') for g in multi))
   self.assertFalse(permitted('oidc:/tenants/a/admins-extra','tenant-a','apps','deployments','patch'))
   self.assertFalse(permitted('oidc:/tenants','tenant-a','apps','deployments','patch'))
   bao=yaml.safe_load((output/'openbao-roles.yaml').read_text())
   for tenant in ['a','b']:
    role=bao['roles'][f'tenant-{tenant}-admin'];self.assertEqual(role['bound_claims'],{'groups':[f'/tenants/{tenant}/admins']})
    policy=bao['policies'][f'proposed-tenant-{tenant}-admin'];self.assertIn(f'tenants/data/{tenant}/*',policy);self.assertNotIn('sys/',policy)
   self.assertTrue(permitted('oidc:/platform/viewers','','','nodes','get'))
   for res,verb in [('secrets','get'),('secrets','list'),('pods','delete')]:self.assertFalse(permitted('oidc:/platform/viewers','tenant-a','',res,verb))
   pa=bao['policies']['proposed-platform-admin']
   self.assertNotIn('path "*"',pa);self.assertNotIn('tenants/data',pa);self.assertNotIn('sudo',pa)
   self.assertIn('path "platform/data/*"',pa)
   self.assertIn('path "tenants/metadata/*" { capabilities = ["list"] }',pa)
   for tenant in ['a','b']:
    dev=bao['policies'][f'proposed-tenant-{tenant}-developer']
    self.assertIn(f'path "tenants/data/{tenant}/*" {{ capabilities = ["read"] }}',dev)
    for mutation in ['create','update','patch','delete','sudo']:self.assertNotIn('"'+mutation+'"',dev)
    view=bao['policies'][f'proposed-tenant-{tenant}-viewer'];self.assertNotIn('tenants/data',view);self.assertNotIn('"read"',view)
   # Small HCL policy model only; real OpenBao capabilities/token-union tests remain a gate.
   def bao_permitted(policy,path,verb):
    for pattern,caps in re.findall(r'path "([^"\n]+)" \{ capabilities = \[([^\]]+)\] \}',policy):
     if fnmatch.fnmatchcase(path,pattern) and verb in re.findall(r'"([^"\n]+)"',caps):return True
    return False
   self.assertTrue(bao_permitted(pa,'platform/data/service/password','read'))
   self.assertTrue(bao_permitted(pa,'platform/data/service/password','update'))
   self.assertTrue(bao_permitted(pa,'tenants/metadata/a','list'))
   self.assertTrue(bao_permitted(pa,'platform/metadata/service/password','read'))
   # KV-v2 metadata UPDATE changes retention; DELETE removes every version.
   for verb in ['create','update','patch','delete']:
    self.assertFalse(bao_permitted(pa,'platform/metadata/service/password',verb))
   for path in ['platform/config','platform/destroy/service/password']:
    self.assertFalse(bao_permitted(pa,path,'update'))
   self.assertTrue(bao_permitted(pa,'platform/data/service/password','delete')) # current-version soft delete

   for path,verb in [('tenants/metadata/a/item','read'),('tenants/data/a/item','read'),('tenants/data/b/item','update'),('sys/policies/acl/self','update'),('auth/oidc/role/self','update')]:self.assertFalse(bao_permitted(pa,path,verb))
   for tenant,other in [('a','b'),('b','a')]:
    for role in ['admin','developer','viewer']:
     policy=bao['policies'][f'proposed-tenant-{tenant}-{role}']
     self.assertFalse(bao_permitted(policy,f'tenants/data/{other}/item','read'))
     self.assertFalse(bao_permitted(policy,'platform/data/service/password','read'))
     self.assertEqual(bao_permitted(policy,f'tenants/data/{tenant}/item','read'),role!='viewer')
     self.assertEqual(bao_permitted(policy,f'tenants/data/{tenant}/item','update'),role=='admin')
     self.assertTrue(bao_permitted(policy,f'tenants/metadata/{tenant}','list'))
     for verb in ['create','update','patch','delete']:
      self.assertFalse(bao_permitted(policy,f'tenants/metadata/{tenant}/item',verb))
     self.assertFalse(bao_permitted(policy,f'tenants/destroy/{tenant}/item','update'))
     self.assertFalse(bao_permitted(policy,'tenants/config','update'))
     if role=='admin':
      self.assertTrue(bao_permitted(policy,f'tenants/metadata/{tenant}/item','read'))
      self.assertTrue(bao_permitted(policy,f'tenants/data/{tenant}/item','delete')) # soft delete only

   self.assertFalse(bao_permitted(bao['policies']['proposed-platform-viewer'],'platform/data/service/password','read'))
   # Engineer scope is not decided: group representation must not self-grant.
   self.assertFalse(permitted('oidc:/platform/engineers','','','nodes','get'))
   self.assertFalse(permitted('oidc:/platform/engineers','tenant-a','','secrets','get'))
   self.assertNotIn('platform-engineer',bao['roles'])
   self.assertNotIn('proposed-platform-engineer',bao['policies'])

   self.assertEqual({x['name'] for x in realm['groups'][0]['subGroups']},{'admins','engineers','viewers'})
   self.assertTrue(all({x['name'] for x in t['subGroups']}=={'admins','developers','viewers'} for t in realm['groups'][1]['subGroups']))
   self.assertTrue((REVIEW/'desired.yaml').is_file())
   p=self.run_play(d,extra);self.assertNotEqual(p.returncode,0) # Never overwrite evidence.
 def test_empty_tenants_and_existing_api_workflow_remain_inactive(self):
  with tempfile.TemporaryDirectory() as d:
   output=Path(d)/'empty';p=self.run_play(d,{'authorization_render':True,'authorization_output_directory':str(output)})
   self.assertEqual(p.returncode,0,p.stdout+p.stderr);realm=yaml.safe_load((output/'realm.yaml').read_text());self.assertEqual(realm['groups'][1]['subGroups'],[])
   play=ROOT/'configuration/ansible/platform-config/configure.yaml'
   for extra,check in [({},False),({},True),({'platform_api_apply':True},True)]:
    p=self.run_play(d,extra,check,play);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('changed=0',p.stdout)

 def test_matrix_and_c4_cover_apps_without_claiming_live_implementation(self):
  matrix=(REVIEW/'MATRIX.md').read_text()
  for label in ['platform-admin','platform-engineer','platform-viewer','tenant-admin','tenant-developer','tenant-viewer','Keycloak','OpenBao','Rancher','Headlamp','Longhorn','Grafana','Mattermost','GitLab','Harbor','SonarQube','portal','Nextcloud','Prometheus','Loki','Alloy','Alertmanager','ntfy','Velero','Trivy','Istio','Gateway API']:
   self.assertIn(label,matrix)
  self.assertIn('not deployed authorization',matrix)
  self.assertIn('not an all-app apply payload',matrix)
  self.assertIn('LIST returns values',matrix)
  self.assertIn('tenant-reader',matrix)
  views=(ROOT.parent/'docs/architecture/views.c4').read_text()
  for view in ['authorization_roles','authorization_core_apps','authorization_observability','authorization_collaboration','authorization_tenant_apps']:
   self.assertIn('view '+view,views)

 def test_contributor_checklist_keeps_matrix_c4_and_permission_tests_together(self):
  guide=(ROOT.parent/'docs/platform/README.md').read_text()
  for contract in ['same MR','role/app matrix','C4 ownership/trust-boundary','positive/negative','proposed / implemented / tested','exceptions or gaps']:
   self.assertIn(contract,guide)
