from pathlib import Path
import importlib.util,json,os,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gitlab_guard',ROOT/'configuration/packages/gitlab/filter_plugins/gitlab_guard.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
class Egress(unittest.TestCase):
 def test_endpoint_policy_separates_jobs_and_manager_without_broad_networks(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-network-fixture-') as directory:
   p=Path(directory);out=p/'out';out.mkdir(mode=0o700)
   v={'gitlab_network_run':True,'gitlab_network_scope':'gitlab-runner-egress-v1','gitlab_network_route_hosts':['192.0.2.20/32','2001:db8::20/128'],'gitlab_network_api_host':'192.0.2.21/32','gitlab_network_api_port':6443,'gitlab_network_traefik_port':8443,'gitlab_private_output_directory':str(out)}
   vf=p/'vars';vf.write_text(json.dumps(v));vf.chmod(0o600)
   def run(check=False):return subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab/prepare-runner-network.yaml'),'-e','@'+str(vf)]+(['--check'] if check else []),env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')},capture_output=True,text=True,timeout=30)
   r=run(True);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse((out/'runner-network.json').exists())
   r=run();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   job,manager=json.loads((out/'runner-network.json').read_text())['items']
   self.assertEqual(job['metadata']['namespace'],'gitlab-ci-platform');self.assertEqual(manager['spec']['podSelector'],{'matchLabels':{'app':'gitlab-runner'}})
   for rule in job['spec']['egress']:self.assertNotIn(6443,[port['port'] for port in rule['ports']])
   self.assertEqual(manager['spec']['egress'][-1]['to'],[{'ipBlock':{'cidr':'192.0.2.21/32'}}])
   peer=job['spec']['egress'][1]['to'];self.assertEqual(len(peer),1);self.assertEqual(set(peer[0]),{'namespaceSelector','podSelector'})
   r=run();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
 def test_wide_invalid_or_local_endpoints_are_refused(self):
  for cidr in ('0.0.0.0/0','::/0','192.0.2.0/24','127.0.0.1/32','169.254.1.1/32','224.0.0.1/32','0.0.0.0/32','::1/128','192.0.2.1/24'):
   with self.subTest(cidr=cidr):self.assertFalse(guard.endpoint_inputs_valid([cidr],'192.0.2.21/32',6443,8443))
  for port in (80,0,65536,True):self.assertFalse(guard.endpoint_inputs_valid(['192.0.2.20/32'],'192.0.2.21/32',port,8443))
  self.assertFalse(guard.endpoint_inputs_valid([],'192.0.2.21/32',6443,8443))
 def test_api_on_job_https_endpoint_is_refused(self):self.assertFalse(guard.endpoint_inputs_valid(['192.0.2.20/32'],'192.0.2.20/32',443,8443))
