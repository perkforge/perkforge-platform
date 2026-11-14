"""Offline additive mounts and no-op safety checks; no runtime credentials."""
import json,subprocess,tempfile,unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
M=ROOT/'configuration/observability/platform-alerts'
A=ROOT/'configuration/packages/ntfy/auth/runtime/platform-audience.yaml'
class PlatformDelivery(unittest.TestCase):
 def test_defaults_and_check_inert(self):
  for file,flag in [(M/'activate.yaml','platform_delivery_activate'),(M/'render-delivery.yaml','platform_delivery_render'),(A,'platform_audience_prepare')]:
   for args in ([],['--check','-e',flag+'=true']):
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(file),*args],capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
 def test_preserve_mounts_and_exact_scope(self):
  with tempfile.TemporaryDirectory() as d:
   prior=[{'name':'existing','mountPath':'/etc/grafana/provisioning/alerting/prior.yaml','secretName':'existing-secret','readOnly':True}]
   v=dict(platform_delivery_render=True,platform_delivery_expected_mounts=prior,platform_delivery_monitoring_namespace='monitoring',platform_delivery_record='observability/platform-alerts-v1',platform_delivery_bao_server='https://bao.example.test',platform_delivery_output_dir=d)
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(M/'render-delivery.yaml'),'-e',json.dumps(v)],capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   mounts=yaml.safe_load((Path(d)/'values.yaml').read_text())['grafana']['values']['upstream']['extraSecretMounts'];self.assertEqual(mounts[:-1],prior);self.assertEqual(mounts[-1]['secretName'],'grafana-platform-alerts')
   docs=list(yaml.safe_load_all((Path(d)/'consumers.yaml').read_text()));role=next(x for x in docs if x['kind']=='Role');self.assertEqual(role['rules'][0]['resourceNames'],['eso-platform-alerts']);self.assertEqual(role['rules'][0]['verbs'],['create'])
   store=next(x for x in docs if x['kind']=='SecretStore');self.assertEqual(store['spec']['provider']['vault']['auth']['kubernetes']['role'],'eso-platform-alerts')
 def test_partial_owner_retry_only_accepts_exact_record(self):
  tasks=yaml.safe_load(A.read_text())[0]['tasks'][0]['block'][-1]['block']
  guard=next(t for t in tasks if t.get('when')=='owner_before.status == 200')
  for actual,expected in [({'username':'corey-platform','token':'synthetic','topic':'platform-alerts'},0),({'username':'corey-platform','token':'different','topic':'platform-alerts'},2)]:
   with tempfile.TemporaryDirectory() as d:
    wrapper=Path(d)/'check.yaml';wrapper.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'owner_before':{'status':200,'json':{'data':{'data':actual}}},'desired_owner':{'username':'corey-platform','token':'synthetic','topic':'platform-alerts'}},'tasks':[{'no_log':True,**guard}]}]))
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(wrapper)],capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,expected);self.assertNotIn('synthetic',r.stdout+r.stderr)
 def test_compare_and_swap_and_no_wildcard(self):
  text=A.read_text();self.assertIn('cas: 0',text);self.assertIn('current.json.data.metadata.version',text);self.assertIn("base['auth-tokens'] == prior_fragment['auth-tokens']",text);self.assertIn('platform_audience_expected_users',text)
  play=yaml.safe_load((M/'activate.yaml').read_text())[0];tasks=play['tasks'][0]['block'];guard=next(x for x in tasks if x.get('name','').startswith('Verify exact existing'));self.assertTrue(guard['no_log']);self.assertIn('== platform_delivery_expected_mounts',guard['block'][1]['ansible.builtin.assert']['that'])
if __name__=='__main__':unittest.main()
