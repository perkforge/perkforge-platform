"""Offline CI selection/permissions tests; no GitHub/cluster calls."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml

spec=importlib.util.spec_from_file_location('ci_impact',Path(__file__).with_name('ci_impact.py'))
impact=importlib.util.module_from_spec(spec);spec.loader.exec_module(impact)

class ImpactTests(unittest.TestCase):
    def test_docs_only_keep_docs_and_skip_unrelated_state_machines(self):
        d=impact.classify(['HANDOFF.md','docs/architecture/views.c4'])
        self.assertTrue(d['docs']);self.assertFalse(d['full'] or d['sso'] or d['headlamp'])
    def test_sso_implementation_runs_all_sso_and_host_boundary_tests(self):
        d=impact.classify(['big-bang-bootstrap/configuration/authorization/sso/tasks/openbao-data.yaml'])
        self.assertTrue(d['sso'] and d['headlamp']);self.assertFalse(d['full'])
    def test_matrix_change_keeps_shared_authorization_model_tests(self):
        d=impact.classify(['big-bang-bootstrap/configuration/authorization/MATRIX.md'])
        self.assertTrue(d['sso'] and d['headlamp']);self.assertFalse(d['full'])

    def test_narrow_test_and_host_changes_select_owner_suite(self):
        for path,key in [('big-bang-bootstrap/tests/integration/test_sso_openbao.py','sso'),('infrastructure/ansible/tasks/api-oidc-apply.yml','headlamp')]:
            d=impact.classify([path]);self.assertTrue(d[key]);self.assertFalse(d['full'])
    def test_shared_dependencies_security_and_unknown_paths_force_full(self):
        for path in ['.github/workflows/gitops-selection.yml','scripts/ci_impact.py','AGENTS.md','release-evidence.json','big-bang-bootstrap/tests/fixtures/selection.py','big-bang-bootstrap/tests/security/test_identity_permissions.py','big-bang-bootstrap/configuration/ansible/tasks/rancher-oidc.yml','big-bang-bootstrap/configuration/authorization/tasks/client.yaml','big-bang-bootstrap/clusters/local/values.yaml','requirements.txt','future/component.py','future/unknown.md']:
            with self.subTest(path=path):self.assertTrue(all(impact.classify([path])[k] for k in ['full','sso','headlamp','docs']))
    def test_mixed_change_unknown_overrides_narrow_and_rename_cannot_hide_it(self):
        self.assertTrue(impact.classify(['docs/a.md','old/shared.py'])['full'])
        self.assertTrue(impact.classify(['big-bang-bootstrap/configuration/authorization/sso/new.yaml','shared.py'])['full'])
    def test_main_manual_missing_and_malformed_impact_force_full(self):
        for event in ['push','workflow_dispatch','workflow_call','unknown']:
            self.assertTrue(impact.classify(['docs/a.md'],event)['full'])
        for paths in [None,[],['../docs/a.md'],['/docs/a.md'],['bad\nname'],[None]]:
            self.assertTrue(impact.classify(paths)['full'])
        self.assertIsNone(impact.changed_paths('missing','missing'))
    def test_deleted_shared_path_is_preserved_by_no_rename_git_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            def git(*args):return subprocess.check_output(['git','-C',tmp,*args],text=True).strip()
            git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            p=Path(tmp)/'shared.py';p.write_text('x=1\n');git('add','.');git('commit','-qm','base');base=git('rev-parse','HEAD')
            (Path(tmp)/'docs').mkdir();p.rename(Path(tmp)/'docs/a.md');git('add','-A');git('commit','-qm','rename');head=git('rev-parse','HEAD')
            original=subprocess.check_output
            with patch.object(impact.subprocess,'check_output',side_effect=lambda args,**kw: original(args,cwd=tmp,**kw)):
                raw=impact.changed_paths(base,head)
            self.assertEqual(set(raw),{'shared.py','docs/a.md'});self.assertTrue(impact.classify(raw)['full'])
    def test_workflow_one_canonical_route_fail_closed_dependencies_and_security(self):
        w=yaml.load(Path('.github/workflows/gitops-selection.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(set(w['on']),{'workflow_call','workflow_dispatch'})
        self.assertEqual(w['permissions'],{'contents':'read'})
        self.assertIn('changes',w['jobs']);self.assertIn('docs',w['jobs'])
        for name,key in [('selection','full'),('platform-sso','sso'),('headlamp-prerequisites','headlamp')]:
            job=w['jobs'][name];self.assertEqual(job['needs'],['changes'])
            self.assertIn(f'needs.changes.outputs.{key}',job['if'])
            self.assertEqual(job['env']['KUBECONFIG'],'/dev/null')
        steps=w['jobs']['selection']['steps'];commands='\n'.join(s.get('run','') for s in steps)
        for required in ['unittest discover -s big-bang-bootstrap/tests','unittest discover -s infrastructure/ansible/tests','unittest discover -s pxe/tests','unittest discover -s evidence/tests','go test -run TestFluxPortalAdmission']:
            self.assertIn(required,commands)
        self.assertTrue(any(s.get('name')=='Verify tag-aware bootstrap without Kubernetes access' for s in steps))
        self.assertIn('test_ci_impact.py','\n'.join(s.get('run','') for s in w['jobs']['changes']['steps']))
    def test_default_unknown_cli_and_missing_git_commits_fail_full(self):
        self.assertIsNone(impact.changed_paths('0'*40,'1'*40))
        r=subprocess.run(['python3','scripts/ci_impact.py','--event','pull_request'],capture_output=True,text=True,check=True)
        self.assertIn('"full": true',r.stdout)

if __name__=='__main__':unittest.main()
