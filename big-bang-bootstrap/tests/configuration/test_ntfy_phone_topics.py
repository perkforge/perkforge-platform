import json,subprocess,tempfile,unittest
from pathlib import Path
import yaml
P=Path(__file__).resolve().parents[2]/'configuration/packages/ntfy/auth/runtime/subscriber-topics.yaml'
class PhoneTopics(unittest.TestCase):
 def test_only_target_topics_change(self):
  tasks=yaml.safe_load(P.read_text())[0]['tasks'][0]['block'][-1]['block'];transform=next(t for t in tasks if t.get('loop')=='{{ prior.accounts }}')
  accounts=[{'username':'corey-portal','topics':['tenant-portal-alerts'],'token':'synthetic-old'},{'username':'grafana-portal','topics':['tenant-portal-alerts'],'token':'synthetic-publisher'}]
  for topics in (['tenant-portal-alerts'],['tenant-portal-alerts','platform-alerts']):
   accounts[0]['topics']=topics
   with tempfile.TemporaryDirectory() as d:
    p=Path(d);play=[{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'prior':{'accounts':accounts},'ntfy_accounts':[],'ntfy_phone_username':'corey-portal','ntfy_phone_add_topic':'platform-alerts'},'tasks':[transform,{'ansible.builtin.copy':{'dest':str(p/'out'),'content':'{{ ntfy_accounts | to_json }}'}}]}];(p/'play').write_text(yaml.safe_dump(play));r=subprocess.run(['ansible-playbook','-i','localhost,',str(p/'play')],capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,0,r.stdout+r.stderr);out=json.loads((p/'out').read_text());self.assertEqual(out[0],{**accounts[0],'topics':['tenant-portal-alerts','platform-alerts']});self.assertEqual(out[1],accounts[1])
if __name__=='__main__':unittest.main()
