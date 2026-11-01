"""Complete rendered object/binding audit, not live Kubernetes authorization proof."""
from pathlib import Path
import unittest,yaml,os,subprocess,tempfile
from fixtures.render_helpers import build,RenderLoader
from fixtures.observability import metrics_render
ROOT=Path(__file__).resolve().parents[2]
class MetricsInstaller(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.render=metrics_render(ROOT);cls.foundation=build(ROOT/'configuration/observability/metrics-prerequisites')
 def allowed(self,identity,kind,group,resource,name,verb):
  return any(group in rule['apiGroups'] and resource in rule['resources'] and verb in rule['verbs'] and ('resourceNames' not in rule or name in rule['resourceNames']) for role in self.foundation if role['kind']==kind and role['metadata']['name']==identity for rule in role['rules'])
 def test_all_objects_and_bindings_are_covered_without_installer_cluster_admin(self):
  mapping={'ServiceAccount':('','serviceaccounts'),'Service':('','services'),'ConfigMap':('','configmaps'),'Secret':('','secrets'),'Deployment':('apps','deployments'),'DaemonSet':('apps','daemonsets'),'PersistentVolumeClaim':('','persistentvolumeclaims'),'Job':('batch','jobs'),'Role':('rbac.authorization.k8s.io','roles'),'RoleBinding':('rbac.authorization.k8s.io','rolebindings'),'PrometheusRule':('monitoring.coreos.com','prometheusrules'),'ServiceMonitor':('monitoring.coreos.com','servicemonitors'),'PodMonitor':('monitoring.coreos.com','podmonitors'),'Prometheus':('monitoring.coreos.com','prometheuses'),'Alertmanager':('monitoring.coreos.com','alertmanagers'),'ClusterRole':('rbac.authorization.k8s.io','clusterroles'),'ClusterRoleBinding':('rbac.authorization.k8s.io','clusterrolebindings'),'MutatingWebhookConfiguration':('admissionregistration.k8s.io','mutatingwebhookconfigurations'),'ValidatingWebhookConfiguration':('admissionregistration.k8s.io','validatingwebhookconfigurations'),'CustomResourceDefinition':('apiextensions.k8s.io','customresourcedefinitions')}
  cluster={'ClusterRole','ClusterRoleBinding','MutatingWebhookConfiguration','ValidatingWebhookConfiguration','CustomResourceDefinition'}
  for name,(hr,objects) in self.render.items():
   identity=hr['spec']['serviceAccountName'];self.assertTrue(hr['spec']['suspend'])
   for obj in objects:
    kind=obj['kind'];group,res=mapping[kind];scope='ClusterRole' if kind in cluster else 'Role'
    for verb in ['get','list','watch','create','update','patch','delete']:self.assertTrue(self.allowed(identity,scope,group,res,obj['metadata']['name'],verb),(name,kind,verb))
    if kind in ['Role','ClusterRole']:self.assertTrue(self.allowed(identity,scope,'rbac.authorization.k8s.io',res,obj['metadata']['name'],'escalate'))
    if kind.endswith('RoleBinding'):
     ref=obj['roleRef'];self.assertTrue(self.allowed(identity,'ClusterRole' if ref['kind']=='ClusterRole' else 'Role','rbac.authorization.k8s.io','clusterroles' if ref['kind']=='ClusterRole' else 'roles',ref['name'],'bind'))
   self.assertFalse(self.allowed(identity,'ClusterRole','rbac.authorization.k8s.io','clusterroles','cluster-admin','bind'))
  self.assertEqual(len(self.render['prometheus-operator-crds'][1]),10)
  self.assertTrue(all(x['metadata']['annotations']['helm.sh/resource-policy']=='keep' for x in self.render['prometheus-operator-crds'][1]))
  self.assertFalse(any(x['kind']=='ClusterRoleBinding' and x['roleRef']['name']=='cluster-admin' for x in self.foundation))
 def test_no_duplicate_grafana_cert_manager_or_broad_grafana_reader(self):
  mon=self.render['monitoring'][1];graf=self.render['grafana'][1]
  self.assertEqual(sum(x['kind']=='PrometheusRule' for x in mon),35)
  self.assertEqual(sum(x['kind']=='Alertmanager' for x in mon),1)
  self.assertFalse(any(x['kind'] in ['Certificate','Issuer'] for x in mon))
  self.assertTrue(any(x['kind']=='Job' and 'patch' in x['metadata']['name'] for x in mon))
  self.assertFalse(any(x['kind'] in ['Role','RoleBinding','ClusterRole','ClusterRoleBinding','Secret','Ingress'] for x in graf))
  reader=next(x for x in self.foundation if x['kind']=='Role' and x['metadata']['name']=='grafana-provisioning-reader')
  self.assertEqual(reader['rules'],[{'apiGroups':[''],'resources':['configmaps'],'verbs':['get','list','watch']}])
  config=next(x for x in graf if x['kind']=='ConfigMap' and 'grafana.ini' in x['data'])['data'];self.assertNotIn('client_secret = secret',config['grafana.ini']);self.assertFalse(yaml.safe_load(config['datasourcesbb.yaml'])['datasources'][0]['editable'])
 def test_six_dashboard_documents_and_safe_applier(self):
  maps=[x for x in self.foundation if x['kind']=='ConfigMap' and x['metadata']['name'].startswith('pf-dashboard')]
  import json
  self.assertEqual(len(maps),6);self.assertEqual(len({json.loads(next(iter(x['data'].values())))['uid'] for x in maps}),6)
  for x in maps:self.assertFalse(json.loads(next(iter(x['data'].values())))['editable'])
  play=ROOT/'configuration/ansible/metrics-prerequisites.yaml';doc=yaml.safe_load(play.read_text())[0];self.assertFalse(doc['vars']['metrics_foundation_apply'])
  with tempfile.TemporaryDirectory() as d:
   p=subprocess.run(['ansible-playbook','-i',str(ROOT/'configuration/ansible/inventory.yaml'),str(play),'--check'],capture_output=True,text=True,env={**os.environ,'ANSIBLE_LOCAL_TEMP':d},timeout=40);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('changed=0',p.stdout)
  self.assertEqual(yaml.load("enum:\n- =\n- '!='\n",Loader=RenderLoader)['enum'],['=','!='])
 def test_selected_real_helm_lookup_path_uses_only_reviewed_api_reads(self):
  from fixtures.lookup_server import lookup_server
  from fixtures.render_helpers import child_values,ordered_values,helm,release_name
  root=build(ROOT/'clusters/local');parent=next(x for x in root if x['kind']=='HelmRelease');src=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
  outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(root,parent)+[(ROOT/'configuration/observability/candidate-values.yaml').read_text()],tuple(y for x in ['monitoring','grafana','prometheusOperatorCRDs'] for y in ['--set',x+'.enabled=true']))
  policy={'metadata':{'namespace':'monitoring'},'rules':[{'apiGroups':[''],'resources':['secrets'],'verbs':['get']}]}
  for name,(hr,objects) in self.render.items():
   with self.subTest(chart=name),tempfile.TemporaryDirectory() as d,lookup_server(policy,secrets={}) as (url,requests):
    p=Path(d);k=p/'kubeconfig';k.write_text(yaml.safe_dump({'apiVersion':'v1','kind':'Config','clusters':[{'name':'synthetic','cluster':{'server':url}}],'users':[{'name':'synthetic','user':{}}],'contexts':[{'name':'synthetic','context':{'cluster':'synthetic','user':'synthetic'}}],'current-context':'synthetic'}))
    values=[]
    for i,s in enumerate(child_values(outer,name)):
     f=p/f'{i}.yaml';f.write_text(s);values+=['-f',str(f)]
    result=subprocess.run(['helm','template',release_name(hr),str(src/name/'chart'),'--namespace',hr['spec']['targetNamespace'],'--kube-version','1.36.5','--kubeconfig',str(k),'--dry-run=server','--include-crds']+values,capture_output=True,text=True,timeout=40)
    self.assertEqual(result.returncode,0,result.stderr)
    parsed=[o for o in yaml.load_all(result.stdout,Loader=RenderLoader) if o];self.assertEqual(len(parsed),len(objects))
    self.assertFalse(any('/clusterroles' in x or '/customresourcedefinitions' in x for x in requests),requests)
