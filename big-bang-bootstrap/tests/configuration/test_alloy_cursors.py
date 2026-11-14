"""Offline native durable cursor proposal. No cluster access or mutation."""
import copy,os,subprocess,tempfile,unittest
from pathlib import Path
import yaml
from fixtures.render_helpers import helm
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'configuration/observability/alloy-cursors'
class AlloyCursors(unittest.TestCase):
 def render(self,out,replicas=0,extra=()):
  return subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'render.yaml'),'-e','alloy_cursor_render=true','-e','alloy_cursor_output='+str(out),'-e',__import__('json').dumps({'alloy_cursor_replicas':replicas}),*extra],capture_output=True,text=True)
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
   for bad in [2,-1,'garbage','0',True,0.5]:
    r=self.render(Path(t)/('bad'+str(bad)),bad);self.assertNotEqual(r.returncode,0)
 def test_stages_preserve_entire_viewer_root(self):
  from fixtures.render_helpers import build
  def idx(name):return {(x['kind'],x.get('metadata',{}).get('namespace'),x['metadata']['name']):x for x in build(ROOT/'clusters'/name)}
  base=idx('local-portal-log-view')
  for name,n in [('local-logging-cursor-prepare',0),('local-logging-cursor-durable',1)]:
   stage=idx(name);self.assertEqual(set(stage)-set(base),{('ConfigMap','bigbang','values-alloy-cursors')})
   for k,v in base.items():
    actual=copy.deepcopy(stage[k])
    if k==('HelmRelease','bigbang','bigbang'):
     self.assertEqual(actual['spec']['valuesFrom'][-1]['name'],'values-alloy-cursors');actual['spec']['valuesFrom'].pop()
    self.assertEqual(v,actual,k)
   with tempfile.TemporaryDirectory() as t:
    r=self.render(Path(t),n);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    self.assertEqual((Path(t)/'values.yaml').read_text(),(SOURCE/f'stage-{n}'/'values.yaml').read_text())
 def test_native_checkpoint_metadata_schema(self):
  import importlib.util,time
  spec=importlib.util.spec_from_file_location('checkpoint',SOURCE/'verify_checkpoint.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  raw=b'positions:\n  ? path: cursor-example/pod:container\n    labels: namespace=example\n  : "1"\n'
  self.assertEqual(m.validate(raw)['targets'],1) # Quiet old offsets are legal.
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'positions.yml';p.write_bytes(raw);self.assertEqual(m.read_bounded(p),raw)
   link=Path(t)/'link';link.symlink_to(p)
   with self.assertRaises(ValueError):m.read_bounded(link)
   p.write_bytes(b'x'*(4*1024*1024+1))
   with self.assertRaises(ValueError):m.read_bounded(p)
   p.unlink();p.mkdir()
   with self.assertRaises(ValueError):m.read_bounded(p)
  for bad in [b'positions: {}',b'not: positions',raw.replace(b'"1"',b'"garbage"'),raw.replace(b'"1"',str(int((time.time()+999)*1000000)).encode()),raw+raw.split(b'positions:\n')[1]]:
   with self.assertRaises(ValueError):m.validate(bad)
 def test_migration_default_and_check_mode_inert(self):
  for name in ['capture','prepare-claim','seed']:
   for extra in [[],['--check','-e',{'capture':'alloy_cursor_capture','prepare-claim':'alloy_cursor_prepare','seed':'alloy_cursor_seed'}[name]+'=true']]:
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/(name+'.yaml')),*extra],capture_output=True,text=True)
    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
 def test_seed_script_refuses_unknown_and_mismatched_content(self):
  play=yaml.safe_load((SOURCE/'seed.yaml').read_text())[0]
  outer=play['tasks'][0]['block'];block=next(x['block'] for x in outer if 'block' in x)
  command=next(x['ansible.builtin.command'] for x in block if x.get('name','').startswith('Refuse unknown'))
  script=command['argv'][-1].replace('{{ cursor_relative_path }}','pod_logs_via_kubernetes_api.feature/loki.source.kubernetes.pod_logs')
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);target=root/'pod_logs_via_kubernetes_api.feature/loki.source.kubernetes.pod_logs/positions.yml'
   local=script.replace('/cursor',str(root))
   raw='positions: example\n'
   def run(data):return subprocess.run(['/bin/sh','-ec',local],input=data,text=True,capture_output=True)
   self.assertEqual(run(raw).returncode,0);self.assertEqual(target.read_text(),raw)
   self.assertEqual(run(raw).returncode,0) # Exact equality retry.
   self.assertNotEqual(run('different').returncode,0);self.assertEqual(target.read_text(),raw)
   (target.parent/'positions.incoming').unlink()
   (root/'unknown').write_text('retain')
   self.assertNotEqual(run(raw).returncode,0);self.assertEqual((root/'unknown').read_text(),'retain')
   (root/'unknown').unlink();lost=root/'lost+found';lost.mkdir()
   self.assertEqual(run(raw).returncode,0)
   (lost/'unexpected').write_text('retain');self.assertNotEqual(run(raw).returncode,0)
   (lost/'unexpected').unlink();lost.rmdir();lost.symlink_to(root/'missing')
   self.assertNotEqual(run(raw).returncode,0)
 def test_seed_rejects_foreign_pvc_user_before_creating_anything(self):
  import json,time
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);binpath=root/'bin';binpath.mkdir();calls=root/'calls'
   fake=binpath/'kubectl'
   fake.write_text("#!/usr/bin/python3\nimport sys,json,os\na=sys.argv[1:]\nwith open(os.environ['CURSOR_CALLS'],'a') as f:f.write(json.dumps(a)+'\\n')\nif 'namespace' in a: print('11111111-1111-1111-1111-111111111111')\nelif 'statefulset' in a: print('{}')\nelif 'deployment' in a: print('')\nelif 'pods' in a: print(json.dumps({'items':[{'metadata':{'name':'unrelated-writer'},'spec':{'volumes':[{'persistentVolumeClaim':{'claimName':'alloy-storage-alloy-alloy-logs-0'}}]}}]}))\nelse: raise SystemExit('Unexpected mutation/query')\n")
   fake.chmod(0o700)
   raw='positions:\n  ? path: cursor-example/pod:container\n    labels: namespace=example\n  : "1"\n';(root/'positions.yml').write_text(raw)
   receipt={'cluster_uid':'11111111-1111-1111-1111-111111111111','captured_at':int(time.time()),'source_mtime':int(time.time()),'image':'registry1.dso.mil/ironbank/opensource/grafana/alloy@sha256:'+'a'*64,'path':'/tmp/alloy/pod_logs_via_kubernetes_api.feature/loki.source.kubernetes.pod_logs/positions.yml','selector':{'app':'collector'},'verification':{'sha256':__import__('hashlib').sha256(raw.encode()).hexdigest()}}
   (root/'receipt.json').write_text(json.dumps(receipt))
   inputs={'alloy_cursor_seed':True,'alloy_cursor_seed_approved':True,'cursor_expected_cluster_uid':receipt['cluster_uid'],'cursor_expected_statefulset_uid':'22222222-2222-2222-2222-222222222222','cursor_expected_claim_uid':'33333333-3333-3333-3333-333333333333','cursor_checkpoint_dir':str(root),'cursor_seeder_image':receipt['image']}
   f=root/'inputs.json';f.write_text(json.dumps(inputs))
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'seed.yaml'),'-e','@'+str(f)],capture_output=True,text=True,env={**os.environ,'PATH':str(binpath)+':'+os.environ['PATH'],'CURSOR_CALLS':str(calls)})
   self.assertNotEqual(r.returncode,0);self.assertIn('unrelated-writer',r.stdout)
   self.assertNotIn('create',calls.read_text());self.assertNotIn('exec',calls.read_text())
 def test_exact_native_controller_and_preserved_container_contract(self):
  chart=os.environ.get('ALLOY_OPERATOR_CHART')
  if not chart:self.skipTest('Exact installed native operator child chart required')
  chart=Path(chart);meta=yaml.safe_load((chart/'Chart.yaml').read_text());self.assertEqual(str(meta['version']),'1.11.0');self.assertEqual(meta['appVersion'],'v1.18.0')
  from fixtures.render_helpers import build,ordered_values,child_values,release_name
  sources=os.environ.get('PREFLIGHT_SOURCES_DIR')
  if not sources:self.skipTest('Exact pinned Big Bang/Alloy fixtures required')
  src=Path(sources);objects=build(ROOT/'clusters/local-portal-log-view')
  parent=next(x for x in objects if x['kind']=='HelmRelease' and x['metadata']['name']=='bigbang')
  maps={x['metadata']['name'] for x in objects if x['kind']=='ConfigMap'}
  missing={x['name'] for x in parent['spec']['valuesFrom'] if x['name'] not in maps}
  # Protected non-Alloy consumers are not needed to render this child. Keep their
  # omission explicit; all checked-in values retain native merge ordering.
  self.assertFalse(any('alloy' in n or 'logging' in n for n in missing),missing)
  parent=copy.deepcopy(parent);parent['spec']['valuesFrom']=[x for x in parent['spec']['valuesFrom'] if x['name'] in maps]
  ordered=ordered_values(objects,parent)
  if parent['spec'].get('values'):ordered.append(yaml.safe_dump(parent['spec']['values']))
  outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered)
  hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='alloy')
  packaged=helm(src/'alloy/chart',release_name(hr),hr['spec']['targetNamespace'],child_values(outer,'alloy'))
  base=next(x['spec'] for x in packaged if x['kind']=='Alloy' and x['metadata']['name']=='alloy-alloy-logs')
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
  self.assertEqual(after['nodeSelector'],{**before.get('nodeSelector',{}),'storage.perkforge.io/worker':'true'})
  self.assertEqual(after['volumes'],[x for x in before['volumes'] if x['name']!='alloy-storage'])
  self.assertFalse(any('hostPath' in v for v in after['volumes']))
  self.assertIn('--storage.path=/tmp/alloy',after['containers'][0]['args'])
  # Every unrelated native object remains identical.
  key=lambda x:(x['kind'],x['metadata']['name'])
  self.assertEqual({key(x):x for x in old if x['kind']!='Deployment'},{key(x):x for x in new if x['kind']!='StatefulSet'})
if __name__=='__main__':unittest.main()
