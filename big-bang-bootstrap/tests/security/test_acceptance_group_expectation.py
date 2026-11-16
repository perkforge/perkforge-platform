"""Literal expectation contract checks; no credentials or native requests."""
import copy,importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).resolve().parents[2]/'configuration/packages/gitlab/enrollment/acceptance/validate.py'
spec=importlib.util.spec_from_file_location('acceptance_expectation_validate',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Expectation(unittest.TestCase):
 def test_exact_alternative_and_binding(self):
  v={'gitlab_acceptance_run':True,'gitlab_acceptance_scope':'tenant-acceptance-project-v1','gitlab_acceptance_context':'portal','gitlab_acceptance_origin':'https://localhost','gitlab_acceptance_ca':'/ca','gitlab_acceptance_source_revision':'a'*40,'gitlab_acceptance_group_expectation':'/group','gitlab_acceptance_actor_id':8}
  g={'stage':'native-group-expectation-v1','context':'portal','origin':'https://localhost','source_revision':'a'*40,'group_id':9,'parent_id':7}
  def check(iv,ig):
   with patch.object(m,'safe'),patch.object(m,'read',side_effect=lambda p:iv if p=='/inputs' else ig):
    return m.check('/token','/receipt','/inputs','validate')
  check(v,g)
  for changes in ({'group_id':True},{'parent_id':0},{'stage':'group-ready'},{'source_revision':'b'*40},{'context':'other'},{'origin':'https://other'},{'extra':'x'}):
   with self.subTest(changes=changes),self.assertRaises(ValueError):check(v,{**g,**changes})
  with self.assertRaises(ValueError):check({**v,'gitlab_acceptance_group_receipt':'/old'},g)
  absent=dict(v);absent.pop('gitlab_acceptance_group_expectation')
  with self.assertRaises(ValueError):check(absent,g)
  legacy=dict(v);legacy.pop('gitlab_acceptance_group_expectation');legacy['gitlab_acceptance_group_receipt']='/old'
  check(legacy,{**g,'stage':'group-ready'})
if __name__=='__main__':unittest.main()
