"""Run the actual native-service binding assertions without a native service."""
import json,subprocess,tempfile,unittest,yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class Binding(unittest.TestCase):
 def test_owned_endpoint_response_guard(self):
  tasks=yaml.safe_load((ROOT/'configuration/packages/gitlab/enrollment/setup/kc-client.yaml').read_text())
  task=next(t for t in tasks if 'ansible.builtin.assert' in t and any('service_user.json.id' in x for x in t['ansible.builtin.assert']['that']))
  uid='11111111-1111-4111-8111-111111111111';name='perkforge-portal-identity-reader'
  with tempfile.TemporaryDirectory() as tmp:
   play=Path(tmp)/'play.yaml';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'tasks':[task]}]))
   for delta,prior,ok in [({},uid,True),({'username':'foreign'},uid,False),({'id':'22222222-2222-4222-8222-222222222222'},uid,False),({'serviceAccountClientId':'foreign'},uid,False),({'serviceAccountClientId':name},uid,True)]:
    data={'reader_name':name,'setup_receipt':{'service_account_id':prior},'service_user':{'json':{'id':uid,'username':'service-account-'+name,**delta}}}
    p=subprocess.run(['ansible-playbook','-i','localhost,',str(play),'-e',json.dumps(data)],capture_output=True,text=True,timeout=15)
    self.assertEqual(p.returncode==0,ok,p.stdout+p.stderr)
if __name__=='__main__':unittest.main()
