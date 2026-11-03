from pathlib import Path
import importlib.util,json,os,shutil,subprocess,tempfile,unittest,yaml
ROOT=Path(__file__).resolve().parents[2];DIRECTORY=ROOT/'configuration/ansible'
spec=importlib.util.spec_from_file_location('foundation_guard',DIRECTORY/'filter_plugins/gitlab_foundation_guard.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
class Foundation(unittest.TestCase):
 def test_create_repeat_foreign_refusal_and_no_existing_patch(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-foundation-api-fixture-') as directory:
   p=Path(directory);stub=p/'kubectl';shutil.copy2(ROOT/'tests/fixtures/gitlab_foundation_cli.py',stub);stub.chmod(0o700)
   state=p/'state';state.write_text(json.dumps({'objects':{},'creates':[]}))
   wrapper=[{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'target_kubeconfig':'synthetic','target_context':'synthetic','gitlab_package_directory':str(ROOT/'configuration/packages'),'gitlab_cnpg_crds':[{'apiVersion':'apiextensions.k8s.io/v1','kind':'CustomResourceDefinition','metadata':{'name':'clusters.postgresql.cnpg.io'},'spec':{'group':'postgresql.cnpg.io','scope':'Namespaced'}}]},'tasks':[{'ansible.builtin.include_tasks':str(DIRECTORY/'tasks/gitlab-foundation.yaml')}]}]
   play=p/'fixture.yaml';play.write_text(yaml.safe_dump(wrapper))
   env={**os.environ,'PATH':str(p)+':'+os.environ['PATH'],'GITLAB_FOUNDATION_TEST_STATE':str(state),'ANSIBLE_FILTER_PLUGINS':str(DIRECTORY/'filter_plugins'),'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')}
   def run():return subprocess.run(['ansible-playbook','-i','localhost,',str(play)],env=env,capture_output=True,text=True,timeout=90)
   first=run();self.assertEqual(first.returncode,0,first.stdout+first.stderr);data=json.loads(state.read_text());self.assertGreater(len(data['creates']),20);count=len(data['creates'])
   second=run();self.assertEqual(second.returncode,0,second.stdout+second.stderr);self.assertIn('changed=0',second.stdout);self.assertEqual(len(json.loads(state.read_text())['creates']),count)
   data=json.loads(state.read_text());target=next(v for v in data['objects'].values() if v['kind']=='ClusterRole');target['rules'].append({'apiGroups':['*'],'resources':['*'],'verbs':['*']});state.write_text(json.dumps(data));before=state.read_bytes();failed=run();self.assertNotEqual(failed.returncode,0);self.assertEqual(state.read_bytes(),before)
   foreign={'apiVersion':'admissionregistration.k8s.io/v1','kind':'ValidatingWebhookConfiguration','metadata':{'name':'cnpg-validating-webhook-configuration'}}
   state.write_text(json.dumps({'objects':{'ValidatingWebhookConfiguration//cnpg-validating-webhook-configuration':foreign},'creates':[]}));before=state.read_bytes();failed=run();self.assertNotEqual(failed.returncode,0);self.assertEqual(state.read_bytes(),before)
 def test_rbac_canonicalization_keeps_default_sa_group_but_rejects_expansion(self):
  desired={'apiVersion':'rbac.authorization.k8s.io/v1','kind':'RoleBinding','metadata':{'name':'owned','namespace':'gitlab','labels':{'perkforge.io/owner':'owned'}},'roleRef':{'apiGroup':'rbac.authorization.k8s.io','kind':'Role','name':'owned'},'subjects':[{'kind':'ServiceAccount','name':'owned','namespace':'bigbang'}]}
  actual=json.loads(json.dumps(desired));actual['subjects'][0]['apiGroup']='';self.assertTrue(guard.matches(actual,desired));actual['subjects'].append({'kind':'User','name':'intruder'});self.assertFalse(guard.matches(actual,desired))
 def test_production_entrypoint_stays_off_and_requires_clean_verified_release(self):
  play=yaml.safe_load((DIRECTORY/'gitlab-prerequisites.yaml').read_text())[0];self.assertFalse(play['vars']['gitlab_foundation_apply']);text=(DIRECTORY/'gitlab-prerequisites.yaml').read_text();self.assertIn('verify-release.yaml',text);self.assertIn('config_release.resolvedCommit',text);self.assertIn('gitlab_foundation_changes.stdout | length == 0',text);self.assertIn('not ansible_check_mode',text)

 def test_crd_known_api_defaults_are_canonical_but_schema_or_scope_drift_refuses(self):
  desired={'apiVersion':'apiextensions.k8s.io/v1','kind':'CustomResourceDefinition','metadata':{'name':'clusters.postgresql.cnpg.io','labels':{'perkforge.io/owner':'platform-cnpg-foundation-v1'}},'spec':{'group':'postgresql.cnpg.io','scope':'Namespaced','versions':[]}}
  actual=json.loads(json.dumps(desired));actual['spec'].update(conversion={'strategy':'None'},preserveUnknownFields=False);self.assertTrue(guard.matches(actual,desired));actual['spec']['scope']='Cluster';self.assertFalse(guard.matches(actual,desired))
