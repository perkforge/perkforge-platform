"""Actual Ansible assertions extracted from source; no API or credentials."""
import copy,os,subprocess,tempfile,unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
A=ROOT/'configuration/packages/gitlab/enrollment/acceptance'
def assertions(value):
 if isinstance(value,dict):
  if 'ansible.builtin.assert' in value:yield value['ansible.builtin.assert']['that']
  for child in value.values():yield from assertions(child)
 elif isinstance(value,list):
  for child in value:yield from assertions(child)
class CurrentUser(unittest.TestCase):
 def test_exact_endpoint_field_shapes_and_version(self):
  files=[A/'authority.yaml',A/'project.yaml',ROOT/'configuration/packages/gitlab-runner/prepare-tenant-acceptance.yaml']
  groups=[list(assertions(yaml.safe_load(p.read_text()))) for p in files]
  expressions=[x for sets in groups for group in sets for x in group if isinstance(x,str) and 'is_admin' in x]
  self.assertEqual(len(expressions),3)
  authority=next(group for group in groups[0] if any('is_admin' in str(x) for x in group))
  user={'id':8,'state':'active','bot':True}
  token={'id':12,'user_id':8,'active':True,'revoked':False,'scopes':['api'],'expires_at':'2099-01-01'}
  def variables(u,version='19.4.2-ee'):
   return {'acceptance_authority':{'results':[{'json':u},{'json':token},{'json':{'version':version}}]},'native':{'results':[{'json':u}]},'gitlab_runner_baseline':{'results':[{'json':{'version':version}},{'json':u}]},'gitlab_acceptance_actor_id':8,'acceptance_today':{'stdout':'2026-11-16'}}
  tasks=[]
  def case(conditions,v,allowed):
   tasks.extend([{'ansible.builtin.assert':{'that':conditions},'vars':v,'register':'guard','ignore_errors':True},{'ansible.builtin.assert':{'that':['guard is succeeded' if allowed else 'guard is failed']}}])
  for expr in expressions:
   case([expr],variables(user),True)
   for value in (False,True,None,'false',0,1,[]):
    case([expr],variables({**user,'is_admin':value}),value is False)
  for version,allowed in [('19.4.2',True),('19.4.2-ee',True),('19.4.3',False)]:case(authority,variables(user,version),allowed)
  with tempfile.TemporaryDirectory(prefix='current-user-assert-') as tmp:
   p=Path(tmp)/'test.yaml';p.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'tasks':tasks}]))
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(p)],capture_output=True,text=True,timeout=60,env={**os.environ,'ANSIBLE_LOCAL_TEMP':tmp+'/local','ANSIBLE_REMOTE_TEMP':tmp+'/remote'})
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
