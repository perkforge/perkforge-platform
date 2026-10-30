"""Default readiness checks are inert; explicit checks observe only, never activate."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
class ReadinessTests(unittest.TestCase):
 def test_default_and_check_mode_never_call_an_api(self):
  for extra in [{},{'platform_readiness_verify':True}]:
   with self.subTest(extra=extra),tempfile.TemporaryDirectory() as directory:
    p=Path(directory);marker=p/'called';stub=p/'kubectl';stub.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\nexit 99\n');stub.chmod(0o700)
    result=subprocess.run(['ansible-playbook','-i',str(ROOT/'configuration/ansible/inventory.yaml'),str(ROOT/'configuration/ansible/readiness.yaml'),'--limit','local','--check','-e',json.dumps(extra)],capture_output=True,text=True,env={**os.environ,'PATH':directory+':'+os.environ['PATH'],'ANSIBLE_LOCAL_TEMP':directory+'/local','ANSIBLE_REMOTE_TEMP':directory+'/remote'})
    self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertFalse(marker.exists());self.assertIn('changed=0',result.stdout)
 def test_explicit_apply_flags_in_check_mode_still_use_no_tools_or_private_inputs(self):
  selections=[('bootstrap',{'bootstrap_apply':True,'bootstrap_verify_release':True}),('headlamp-prerequisites',{'foundation_apply':True,'headlamp_registry_apply':True}),('keycloak-prerequisites',{'identity_foundation_apply':True,'identity_routing_apply':True,'identity_access_apply':True})]
  for name,extra in selections:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as directory:
    p=Path(directory);marker=p/'called'
    for tool in ['kubectl','gh','git','curl','ssh']:
     stub=p/tool;stub.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\nexit 99\n');stub.chmod(0o700)
    result=subprocess.run(['ansible-playbook','-i',str(ROOT/'configuration/ansible/inventory.yaml'),str(ROOT/'configuration/ansible'/(name+'.yaml')),'--limit','local','--check','-e',json.dumps(extra)],capture_output=True,text=True,env={**os.environ,'PATH':directory+':'+os.environ['PATH'],'ANSIBLE_LOCAL_TEMP':directory+'/local','ANSIBLE_REMOTE_TEMP':directory+'/remote'})
    self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertFalse(marker.exists());self.assertIn('changed=0',result.stdout)
 def test_readiness_order_does_not_mutate_or_replace_source_selection(self):
  play=yaml.safe_load((ROOT/'configuration/ansible/readiness.yaml').read_text())[0];self.assertFalse(play['vars']['platform_readiness_verify'])
  block=play['tasks'][1]['block'];rollout=next(t for t in block if t.get('name','').startswith('Wait database'))
  self.assertEqual([x['resource'] for x in rollout['loop']],['statefulset/keycloak-postgresql','statefulset/keycloak-keycloak','deployment/headlamp-headlamp'])
  text=(ROOT/'configuration/ansible/readiness.yaml').read_text()
  for command in [', apply,',', patch,',', scale,',', delete,']:self.assertNotIn(command,text)
  self.assertIn('readiness_uid.stdout == expected_cluster_uid',text)
  self.assertFalse((ROOT/'stages').exists())
if __name__=='__main__':unittest.main()
