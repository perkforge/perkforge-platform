"""Pinned rendered logging contracts; no claim of operator/live acceptance."""
from pathlib import Path
import unittest,yaml,re,json,subprocess,tempfile,os
from fixtures.observability import logging_render
from fixtures.render_helpers import build
ROOT=Path(__file__).resolve().parents[2]
class LoggingInstaller(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.render=logging_render(ROOT);cls.foundation=build(ROOT/'configuration/observability/logging-prerequisites')
 def test_all_rendered_objects_and_role_delegations(self):
  mapping={'ServiceAccount':('','serviceaccounts'),'Service':('','services'),'ConfigMap':('','configmaps'),'Deployment':('apps','deployments'),'StatefulSet':('apps','statefulsets'),'Job':('batch','jobs'),'Role':('rbac.authorization.k8s.io','roles'),'RoleBinding':('rbac.authorization.k8s.io','rolebindings'),'CustomResourceDefinition':('apiextensions.k8s.io','customresourcedefinitions'),'Alloy':('collectors.grafana.com','alloys')}
  for package,(hr,objects) in self.render.items():
   identity=hr['spec']['serviceAccountName'];self.assertTrue(hr['spec']['suspend'])
   def allowed(kind,group,res,name,verb):
    return any(group in r['apiGroups'] and res in r['resources'] and verb in r['verbs'] and ('resourceNames' not in r or name in r['resourceNames']) for x in self.foundation if x['kind']==kind and x['metadata']['name']==identity for r in x['rules'])
   for x in objects:
    group,res=mapping[x['kind']];scope='ClusterRole' if x['kind']=='CustomResourceDefinition' else 'Role'
    for verb in ['get','list','watch','create','update','patch','delete']:self.assertTrue(allowed(scope,group,res,x['metadata']['name'],verb),(package,x['kind'],x['metadata']['name'],verb))
    if x['kind']=='Role':self.assertTrue(allowed('Role',group,res,x['metadata']['name'],'escalate'))
    if x['kind']=='RoleBinding':self.assertTrue(allowed('Role',group,'roles',x['roleRef']['name'],'bind'))
   self.assertFalse(allowed('ClusterRole','rbac.authorization.k8s.io','clusterroles','cluster-admin','bind'))
  self.assertFalse(any(x['kind'] in ['ClusterRole','ClusterRoleBinding'] for _,ds in self.render.values() for x in ds))
 def test_authenticated_tls_loki_and_retention(self):
  ds=self.render['loki'][1];config=next(x for x in ds if x['kind']=='ConfigMap' and 'config.yaml' in x.get('data',{}));c=yaml.safe_load(config['data']['config.yaml'])
  self.assertTrue(c['auth_enabled']);self.assertEqual(c['limits_config']['retention_period'],'72h');self.assertTrue(c['compactor']['retention_enabled']);self.assertEqual(c['storage_config']['filesystem']['directory'],'/var/loki/chunks');self.assertFalse(c['limits_config']['max_line_size_truncate'])
  gateway=next(x for x in ds if x['kind']=='ConfigMap' and 'nginx.conf' in x.get('data',{}))['data']['nginx.conf']
  for token in ['listen             8080 ssl','auth_basic_user_file','proxy_ssl_verify on','proxy_set_header X-Scope-OrgID $remote_user','proxy_set_header Authorization ""']:self.assertIn(token,gateway)
  self.assertNotIn('$http_x_scope_orgid',gateway)
  self.assertFalse(any(x['kind']=='Secret' for x in ds))
  for x in ds:
   if x['kind'] in ['Deployment','StatefulSet']:self.assertEqual(x['spec']['template']['spec']['securityContext']['seccompProfile']['type'],'RuntimeDefault')
  self.assertEqual(next(x for x in ds if x['kind']=='StatefulSet')['spec']['volumeClaimTemplates'][0]['spec']['resources']['requests']['storage'],'10Gi')
 def test_api_collector_is_scoped_without_host_mounts_or_operator_cluster_grants(self):
  ds=self.render['alloy'][1];cr=next(x for x in ds if x['kind']=='Alloy')['spec'];self.assertEqual(cr['controller']['type'],'deployment');self.assertFalse(cr['rbac']['create']);self.assertEqual(cr['serviceAccount']['name'],'alloy-log-reader')
  self.assertFalse(cr['alloy']['mounts']['varlog']);self.assertFalse(cr['alloy']['mounts']['dockercontainers']);self.assertEqual(cr['alloy']['securityContext']['capabilities'],{'drop':['ALL'],'add':[]})
  text=next(x for x in ds if x['kind']=='ConfigMap')['data']['config.alloy'];self.assertIn('names = ["logging-pilot"]',text);self.assertIn('observability.perkforge.io/logs=true',text);self.assertIn('ca_file = "/loki-ca/ca.crt"',text);self.assertIn('insecure_skip_verify = false',text);self.assertNotIn('loki.secretfilter',text)
  expression=next(x.split('=',1)[1].strip() for x in text.splitlines() if '(?i)' in x);pattern=json.loads(expression);regex=re.compile(pattern);sample='password=example token: example2 normal';masked=regex.sub(lambda m:m.group().replace(m.group('sensitive'),'REDACTED'),sample);self.assertEqual(masked,'password=REDACTED token: REDACTED normal')
  reader=next(x for x in self.foundation if x['kind']=='Role' and x['metadata']['name']=='alloy-pod-log-reader');self.assertEqual(reader['metadata']['namespace'],'logging-pilot');self.assertNotIn('secrets',reader['rules'][0]['resources'])
 def test_default_off_and_network_bypass_boundary(self):
  play=ROOT/'configuration/ansible/logging-prerequisites.yaml';self.assertFalse(yaml.safe_load(play.read_text())[0]['vars']['logging_foundation_apply'])
  with tempfile.TemporaryDirectory() as d:
   p=subprocess.run(['ansible-playbook','-i',str(ROOT/'configuration/ansible/inventory.yaml'),str(play),'--check'],capture_output=True,text=True,env={**os.environ,'ANSIBLE_LOCAL_TEMP':d},timeout=40);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('changed=0',p.stdout)
  policy=next(x for x in self.foundation if x['kind']=='NetworkPolicy' and x['metadata']['name']=='authenticated-loki-clients');self.assertEqual(policy['spec']['podSelector']['matchLabels']['app.kubernetes.io/component'],'gateway')
