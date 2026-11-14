"""Offline native durable cursor proposal. No cluster access or mutation."""
import copy,os,subprocess,tempfile,unittest
from pathlib import Path
import yaml
from fixtures.render_helpers import helm
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'configuration/observability/alloy-cursors'
class AlloyCursors(unittest.TestCase):
 def render(self,out,replicas=0,extra=()):
  return subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'render.yaml'),'-e','alloy_cursor_render=true','-e','alloy_cursor_output='+str(out),'-e','alloy_cursor_replicas='+str(replicas),*extra],capture_output=True,text=True)
 def test_default_and_check_mode_inert(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'out'
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'render.yaml'),'-e','alloy_cursor_output='+str(out)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse(out.exists())
   r=self.render(out,extra=('--check',));self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse(out.exists())
 def test_bounded_stages_differ_only_replicas(self):
  with tempfile.TemporaryDirectory() as t:
   docs=[]
   for n in [0,1]:
    out=Path(t)/str(n);r=self.render(out,n);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    docs.append(yaml.safe_load((out/'values.yaml').read_text()))
   a,b=docs; ac=a['alloy']['values']['upstream']['collectors']['alloy-logs']['controller'];bc=b['alloy']['values']['upstream']['collectors']['alloy-logs']['controller']
   self.assertEqual(ac['replicas'],0);self.assertEqual(bc['replicas'],1);ac['replicas']=1;self.assertEqual(a,b)
   self.assertFalse(ac['enableStatefulSetAutoDeletePVC']);self.assertFalse(ac['parallelRollout'])
   r=self.render(Path(t)/'bad',2);self.assertNotEqual(r.returncode,0)
 def test_exact_native_controller_and_preserved_container_contract(self):
  chart=os.environ.get('ALLOY_OPERATOR_CHART')
  if not chart:self.skipTest('Exact installed native operator child chart required')
  chart=Path(chart);meta=yaml.safe_load((chart/'Chart.yaml').read_text());self.assertEqual(str(meta['version']),'1.11.0');self.assertEqual(meta['appVersion'],'v1.18.0')
  base=yaml.safe_load((ROOT/'configuration/observability/integrated-logging/values.yaml').read_text())['alloy']['values']['upstream']['collectors']['alloy-logs']
  base=copy.deepcopy(base);base['controller']['type']='deployment';base['controller']['replicas']=1
  # Same singleton restricted runtime contract as pinned BB output; no credentials.
  base['alloy']['securityContext']={'runAsNonRoot':True,'runAsUser':473,'runAsGroup':473,'readOnlyRootFilesystem':True,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}}
  base['global']={'podSecurityContext':{'fsGroup':473}}
  old=helm(chart,'alloy-alloy-logs','alloy',[yaml.safe_dump(base)])
  dep=next(x for x in old if x['kind']=='Deployment')
  with tempfile.TemporaryDirectory() as t:
   r=self.render(Path(t),1);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   delta=yaml.safe_load((Path(t)/'values.yaml').read_text())['alloy']['values']['upstream']['collectors']['alloy-logs']
   new=helm(chart,'alloy-alloy-logs','alloy',[yaml.safe_dump(base),yaml.safe_dump(delta)])
  self.assertFalse(any(x['kind']=='Deployment' for x in new));sts=next(x for x in new if x['kind']=='StatefulSet')
  self.assertEqual(sts['spec']['replicas'],1);self.assertNotIn('persistentVolumeClaimRetentionPolicy',sts['spec'])
  self.assertNotEqual(sts['spec'].get('podManagementPolicy'),'Parallel')
  claim=sts['spec']['volumeClaimTemplates'][0];self.assertEqual(claim['metadata']['name'],'alloy-storage');self.assertEqual(claim['spec']['accessModes'],['ReadWriteOnce']);self.assertEqual(claim['spec']['resources']['requests']['storage'],'1Gi')
  before=dep['spec']['template']['spec'];after=sts['spec']['template']['spec']
  self.assertEqual(before['containers'],after['containers'])
  self.assertEqual(after['nodeSelector'],{'storage.perkforge.io/worker':'true'})
  self.assertEqual(after['volumes'],[x for x in before['volumes'] if x['name']!='alloy-storage'])
  self.assertFalse(any('hostPath' in v for v in after['volumes']))
  self.assertIn('--storage.path=/tmp/alloy',after['containers'][0]['args'])
  # Every unrelated native object remains identical.
  key=lambda x:(x['kind'],x['metadata']['name'])
  self.assertEqual({key(x):x for x in old if x['kind']!='Deployment'},{key(x):x for x in new if x['kind']!='StatefulSet'})
if __name__=='__main__':unittest.main()
