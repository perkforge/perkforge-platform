import json,os,subprocess,tempfile,unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'configuration/packages/gitlab/enrollment/acceptance/manager'
class Manager(unittest.TestCase):
 def test_default_and_scoped_render(self):
  self.assertEqual(subprocess.check_output(['bash',str(D/'render.sh')],text=True).strip(),'INERT')
  with tempfile.TemporaryDirectory(prefix='tenant-manager-') as tmp:
   p=Path(tmp);p.chmod(0o700)
   for context in ('portal','atlas','a'*31):
    out=p/context;out.mkdir(mode=0o700);i=p/(context+'.json');i.write_text(json.dumps({'context':context,'gitlab_origin':'https://gitlab.example.test','output_directory':str(out)}));i.chmod(0o600)
    result=subprocess.run(['bash',str(D/'render.sh'),'--render',str(i)],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    foundation=list(yaml.safe_load_all((out/'foundation.yaml').read_text()));release=list(yaml.safe_load_all((out/'release.yaml').read_text()))
    ns={x['metadata']['name'] for x in foundation if x['kind']=='Namespace'};self.assertEqual(ns,{'gitlab-tenant-'+context+'-runner','gitlab-tenant-'+context+'-ci'})
    self.assertFalse(any(x['kind'] in ('ClusterRole','ClusterRoleBinding','Secret') for x in foundation))
    self.assertTrue(all(x['metadata'].get('namespace') in ns for x in foundation if x['kind']!='Namespace'))
    self.assertTrue(release[1]['spec']['suspend']);u=release[1]['spec']['values']['upstream'];self.assertFalse(u['rbac']['create']);self.assertFalse(u['rbac']['clusterWideAccess']);self.assertFalse(u['unregisterRunners']);self.assertEqual(u['concurrent'],1)
    c=u['runners']['config'];self.assertIn('namespace = "gitlab-tenant-'+context+'-ci"',c);self.assertIn('automount_service_account_token = false',c);self.assertIn('privileged = false',c)
    self.assertNotIn('gitlab-ci-platform',c);self.assertFalse(release[1]['spec']['values']['autoRegister']['enabled'])
    self.assertNotEqual(subprocess.run(['bash',str(D/'render.sh'),'--render',str(i)],capture_output=True).returncode,0)
   reserved=p/'reserved.json';reserved.write_text(json.dumps({'context':'platform','gitlab_origin':'https://gitlab.example.test','output_directory':str(p)}));reserved.chmod(0o600)
   self.assertNotEqual(subprocess.run(['bash',str(D/'render.sh'),'--render',str(reserved)],capture_output=True).returncode,0)
   i=p/'bad.json';i.write_text(json.dumps({'context':'{{ lookup("pipe","false") }}','gitlab_origin':'https://gitlab.example.test','output_directory':str(p)}));i.chmod(0o600)
   self.assertNotEqual(subprocess.run(['bash',str(D/'render.sh'),'--render',str(i)],capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()
