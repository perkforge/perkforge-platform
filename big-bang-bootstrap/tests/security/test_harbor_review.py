from pathlib import Path
import unittest,yaml,os,subprocess,tempfile
from fixtures.collaboration import package_render
from fixtures.render_helpers import build,ordered_values,helm,child_values,release_name
ROOT=Path(__file__).resolve().parents[2]
class HarborReview(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.hr,cls.objects=package_render(ROOT,'harbor')['harbor'];cls.foundation=build(ROOT/'configuration/packages/harbor/prerequisites')
 def test_inactive_secret_refs_and_no_sample_credentials(self):
  c=yaml.safe_load((ROOT/'configuration/packages/harbor/candidate-values.yaml').read_text())['addons']['harbor'];self.assertFalse(c['enabled']);self.assertTrue(self.hr['spec']['suspend']);self.assertFalse(c['values']['upstream']['trivy']['enabled'])
  self.assertEqual(len(self.objects),23);self.assertFalse(any(x['kind'] in ['Ingress','Gateway','HTTPRoute','Role','ClusterRole','RoleBinding','ClusterRoleBinding','CustomResourceDefinition'] for x in self.objects))
  for x in self.objects:
   if x['kind']=='Secret':self.assertFalse(x.get('data'));self.assertFalse(x.get('stringData'))
  self.assertNotIn('harborPW',yaml.safe_dump(self.objects));self.assertNotIn('changeit',yaml.safe_dump(self.objects))
  registry=next(x for x in self.objects if x['kind']=='PersistentVolumeClaim' and x['metadata']['name']=='harbor-registry')
  self.assertEqual(registry['spec']['storageClassName'],'longhorn-dedicated')
  self.assertEqual(registry['spec']['resources']['requests']['storage'],'10Gi')
 def test_all_rendered_crud_with_no_cluster_or_bind_authority(self):
  rules=next(x for x in self.foundation if x['kind']=='Role')['rules'];mapping={'Secret':('','secrets'),'ConfigMap':('','configmaps'),'Service':('','services'),'PersistentVolumeClaim':('','persistentvolumeclaims'),'Deployment':('apps','deployments')}
  for x in self.objects:
   group,res=mapping[x['kind']]
   for verb in ['get','list','watch','create','update','patch','delete']:self.assertTrue(any(group in r['apiGroups'] and res in r['resources'] and verb in r['verbs'] for r in rules))
  self.assertFalse(any(x['kind'] in ['ClusterRole','ClusterRoleBinding'] for x in self.foundation));self.assertFalse(any('bind' in x['verbs'] or 'escalate' in x['verbs'] for x in rules))
 def test_real_initial_and_upgrade_lookups_without_secret_output(self):
  from fixtures.lookup_server import lookup_server
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);root=build(ROOT/'clusters/local');parent=next(x for x in root if x['kind']=='HelmRelease');outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(root,parent)+[(ROOT/'configuration/packages/harbor/candidate-values.yaml').read_text()],('--set','addons.harbor.enabled=true'));role=next(x for x in self.foundation if x['kind']=='Role')
  for upgrade in [False,True]:
   with tempfile.TemporaryDirectory() as d,lookup_server(role,secrets={}) as (url,requests):
    p=Path(d);k=p/'kubeconfig';k.write_text(yaml.safe_dump({'apiVersion':'v1','kind':'Config','clusters':[{'name':'synthetic','cluster':{'server':url}}],'users':[{'name':'synthetic','user':{}}],'contexts':[{'name':'synthetic','context':{'cluster':'synthetic','user':'synthetic'}}],'current-context':'synthetic'}));args=[]
    for i,v in enumerate(child_values(outer,'harbor')):
     f=p/f'{i}.yaml';f.write_text(v);args+=['-f',str(f)]
    r=subprocess.run(['helm','template',release_name(self.hr),str(src/'harbor/chart'),'--namespace','harbor','--kube-version','1.36.5','--kubeconfig',str(k),'--dry-run=server']+(['--is-upgrade'] if upgrade else [])+args,capture_output=True,text=True,timeout=40);self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(any('/clusterroles' in x for x in requests),requests)

 def test_installer_identity_namespace_matches_flux_helmrelease(self):
  name=self.hr['spec']['serviceAccountName'];namespace=self.hr['metadata']['namespace'];sa=next(x for x in self.foundation if x['kind']=='ServiceAccount' and x['metadata']['name']==name);self.assertEqual(sa['metadata']['namespace'],namespace);self.assertFalse(sa['automountServiceAccountToken'])
  role=next(x for x in self.foundation if x['kind']=='Role' and x['metadata']['name']==name)
  for group,res in [('', 'pods'),('apps','replicasets')]:self.assertTrue(any(group in r['apiGroups'] and res in r['resources'] and set(['get','list','watch']).issubset(r['verbs']) and not set(['create','patch','update','delete']).intersection(r['verbs']) for r in role['rules']))
  subjects=[q for x in self.foundation if x['kind'].endswith('RoleBinding') for q in x['subjects'] if q['name']==name];self.assertTrue(subjects);self.assertTrue(all(q['namespace']==namespace for q in subjects))

 def test_external_redis_tls_and_public_ca_references_render_natively(self):
  core=next(x['data'] for x in self.objects if x['kind']=='ConfigMap' and '_REDIS_URL_CORE' in x.get('data',{}))
  self.assertTrue(core['_REDIS_URL_CORE'].startswith('rediss://'))
  self.assertEqual(core['POSTGRESQL_SSLMODE'],'verify-full')
  registry=next(yaml.safe_load(x['data']['config.yml']) for x in self.objects if x['kind']=='ConfigMap' and 'config.yml' in x.get('data',{}) and 'redis:' in x['data']['config.yml'])
  self.assertTrue(registry['redis']['enableTLS'])
  consumers=0
  for obj in self.objects:
   if obj['kind']!='Deployment':continue
   pod=obj['spec']['template']['spec']
   self.assertTrue(all(v.get('secret') and v['secret'].get('secretName') for v in pod.get('volumes',[]) if 'secret' in v),obj['metadata']['name'])
   volumes={v['name'] for v in pod.get('volumes',[]) if (v.get('secret') or {}).get('secretName')=='harbor-public-ca'}
   if volumes:
    consumers+=1
    self.assertTrue(any(m['name'] in volumes and m['mountPath']=='/harbor_cust_cert/custom-ca.crt' and m['subPath']=='ca.crt' for c in pod['containers'] for m in c.get('volumeMounts',[])))
  self.assertGreaterEqual(consumers,3)

 def test_core_database_driver_explicitly_selects_the_mounted_public_ca(self):
  core=next(x for x in self.objects if x['kind']=='Deployment' and x['metadata']['name']=='harbor-core')
  pod=core['spec']['template']['spec'];container=next(c for c in pod['containers'] if c['name']=='core')
  root=next((x for x in container.get('env',[]) if x['name']=='PGSSLROOTCERT'),None)
  self.assertIsNotNone(root,'A custom CA mount alone does not select the PostgreSQL driver trust root')
  self.assertEqual(root,{'name':'PGSSLROOTCERT','value':'/harbor_cust_cert/custom-ca.crt'})
  mount=next(x for x in container['volumeMounts'] if x['mountPath']==root['value'])
  self.assertEqual(mount['subPath'],'ca.crt')
  volume=next(v for v in pod['volumes'] if v['name']==mount['name'])
  self.assertEqual(volume['secret']['secretName'],'harbor-public-ca')

 def test_core_database_pool_limits_reach_native_configuration(self):
  core=next(x['data'] for x in self.objects if x['kind']=='ConfigMap' and 'POSTGRESQL_MAX_OPEN_CONNS' in x.get('data',{}))
  self.assertEqual(core['POSTGRESQL_MAX_OPEN_CONNS'],'50','Do not silently restore the chart 1000-connection pool')
  self.assertEqual(core['POSTGRESQL_MAX_IDLE_CONNS'],'10','Do not silently restore the native 100 idle connections')
