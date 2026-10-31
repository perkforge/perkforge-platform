"""Read-only preflight default/check refusal and missing-prerequisite reporting."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parent

class LonghornPreflightTests(unittest.TestCase):
 def test_default_and_check_mode_never_contact_hosts(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);marker=p/'contacted'
   for tool in ['ssh','kubectl']:
    stub=p/tool;stub.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\nexit 99\n');stub.chmod(0o700)
   for flags in [[],['--check','-e','longhorn_preflight_verify=true']]:
    result=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'longhorn-preflight.yml'),*flags],capture_output=True,text=True,timeout=20,env={**os.environ,'PATH':temp+':'+os.environ['PATH'],'ANSIBLE_LOCAL_TEMP':temp+'/local','ANSIBLE_REMOTE_TEMP':temp+'/remote'})
    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    self.assertFalse(marker.exists())

 def test_report_retains_missing_checks_instead_of_claiming_install_readiness(self):
  task=yaml.safe_load((ROOT/'longhorn-preflight-node.yml').read_text())[-1]
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);fixture=p/'fixture.yml'
   observations={'results':[{'item':{'name':'iscsi_package'},'rc':1,'stdout':'not installed'}, {'item':{'name':'selinux'},'rc':0,'stdout':'Enforcing'}]}
   fixture.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'preflight_node':'fixture-worker','preflight_reports':[],'preflight_observations':observations},'tasks':[task,{'ansible.builtin.copy':{'dest':str(p/'report.json'),'content':'{{ preflight_reports | to_json }}','mode':'0600'}}]}]))
   result=subprocess.run(['ansible-playbook','-i','localhost,',str(fixture)],capture_output=True,text=True,timeout=20,env={**os.environ,'ANSIBLE_LOCAL_TEMP':temp+'/local','ANSIBLE_REMOTE_TEMP':temp+'/remote'})
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   report=json.loads((p/'report.json').read_text())[0]
   self.assertEqual(report['unmet_checks'],['iscsi_package'])
   self.assertIn('unverified',report['selinux_runtime_policy'])

if __name__=='__main__':unittest.main()
