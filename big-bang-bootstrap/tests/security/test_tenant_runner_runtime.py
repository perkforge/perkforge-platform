import json,subprocess,tempfile,unittest
from pathlib import Path
import yaml
D=Path(__file__).resolve().parents[2]/'configuration/packages/gitlab/enrollment/acceptance/manager'
class Runtime(unittest.TestCase):
 def test_scoped_runtime_and_rejections(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);p.chmod(0o700);out=p/'out';out.mkdir(mode=0o700)
   data={'context':'portal','gitlab_origin':'https://gitlab.example.test','output_directory':str(out),'runtime':{'bao_server':'https://bao.example.test','route_hosts':['192.0.2.10/32'],'api_host':'192.0.2.11/32','api_port':6443,'traefik_port':8443}}
   inp=p/'input.json'
   def run():
    inp.write_text(json.dumps(data));inp.chmod(0o600)
    return subprocess.run(['bash',str(D/'render.sh'),'--render',str(inp)],capture_output=True,text=True)
   result=run();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   docs=list(yaml.safe_load_all((out/'runtime.yaml').read_text()));es=next(x for x in docs if x['kind']=='ExternalSecret')
   self.assertEqual(es['spec']['target']['creationPolicy'],'Merge');self.assertEqual(es['spec']['target']['template']['data'],{'runner-registration-token':'','runner-token':'{{ .runnerToken }}'})
   for x in docs:
    if x['kind']!='NetworkPolicy':self.assertEqual(x['metadata']['namespace'],'gitlab-tenant-portal-runner')
   policies=[x for x in docs if x['kind']=='NetworkPolicy'];self.assertEqual(len(policies),2)
   job=next(x for x in policies if x['metadata']['namespace'].endswith('-ci'))
   self.assertNotIn('6443',json.dumps(job));self.assertNotIn('0.0.0.0/0',json.dumps(docs))
   role=next(x for x in docs if x['kind']=='Role');secret=next(x for x in role['rules'] if x['resources']==['secrets']);self.assertEqual(secret['resourceNames'],['gitlab-runner-auth']);self.assertNotIn('create',secret['verbs'])
   self.assertIn('platform/data/gitlab/tenant-portal/acceptance-runner-v1',(out/'runner-policy.hcl').read_text())
   for n,bad in enumerate([{'api_host':'192.0.2.10/32','api_port':443},{'route_hosts':[3221225994]},{'route_hosts':['192.0.2.10']},{'api_host':3221225995},{'route_hosts':['0.0.0.0/0']},{'api_host':'127.0.0.1/32'},{'api_port':True},{'bao_server':'http://unsafe'},{'unexpected':'x'}]):
    fresh=p/str(n);fresh.mkdir(mode=0o700);data['output_directory']=str(fresh);base=data['runtime'].copy();data['runtime'].update(bad);self.assertNotEqual(run().returncode,0);data['runtime']=base
if __name__=='__main__':unittest.main()
