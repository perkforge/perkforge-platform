"""Pure context authority contract, no credentials/native operations."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'configuration/packages/gitlab/enrollment/identity_context.py'
spec=importlib.util.spec_from_file_location('contract',P);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class Contract(unittest.TestCase):
 def test_portal_legacy_exact(self):
  d=c.derive('portal')
  self.assertEqual(c.policy_text('portal'),(P.parent/'setup/keycloak-custody-policy.hcl').read_text())
  self.assertEqual(d['writer_namespace'],'tenant-identity-writer')
  self.assertEqual(d['evidence_name'],'portal-identity-evidence')
 def test_alternate_isolated_shared_gitlab(self):
  a,b=c.derive('portal'),c.derive('workshop')
  for k in ('client_id','record','bootstrap_policy','eso_role','eso_service_account','writer_namespace','attestor_namespace','writer_eso_role','reader_eso_role','evidence_name','digest'):
   self.assertNotEqual(a[k],b[k],k)
  for k in ('gitlab_writer_record','gitlab_reader_record'):self.assertEqual(a[k],b[k])
  self.assertNotIn('portal',c.policy_text('workshop'))
  self.assertNotIn('*',c.policy_text('workshop'))
  self.assertEqual(c.derive('workshop'),b)
 def test_literal_reserved_and_bounds(self):
  for bad in ('', 'platform','tenants','system','default','Portal','../portal','foo/bar','foo*','{{lookup(x)}}','a'*32,'foo-',None,{}):
   with self.assertRaises(ValueError):c.derive(bad)
  d=c.derive('a'*31)
  for key in ('writer_namespace','attestor_namespace','writer_eso_role','reader_eso_role','eso_role','evidence_name'):self.assertLessEqual(len(d[key]),63)

class PhaseBinding(unittest.TestCase):
 def test_alternate_namespace_digest_and_recomputed_crossed_invocation(self):
  import hashlib,json,tempfile
  spec=importlib.util.spec_from_file_location('phase',P.parent/'phases/contract.py');phase=importlib.util.module_from_spec(spec);spec.loader.exec_module(phase)
  selected=c.derive('workshop')
  d={'identity_run':True,'identity_scope':'gitlab-identity-attest-v1','identity_context':'workshop','identity_context_digest':selected['digest'],'identity_source_revision':'a'*40,'identity_platform_revision':'b'*40,'identity_contract_sha256':'c'*64,'identity_previous_invocation':'','identity_retry_generation':0,'identity_gitlab_origin':'https://gitlab.example.test','identity_keycloak_origin':'https://keycloak.example.test/auth','identity_keycloak_realm':'example','identity_kubernetes_origin':'https://kubernetes.default.svc','identity_receipt_uid':'00000000-0000-4000-8000-000000000001','identity_receipt_namespace':selected['writer_namespace'],'identity_receipt_name':selected['evidence_name'],'identity_membership_recovery_verified':False,'identity_group_ids':{r:f'00000000-0000-4000-8000-{i:012d}' for i,r in enumerate(sorted(phase.ROLES),1)}}
  with tempfile.TemporaryDirectory() as directory:
   f=Path(directory)/'phase.json'
   def check(value):
    value=dict(value);material={k:v for k,v in value.items() if k not in ('identity_invocation','identity_scope','identity_run')};value['identity_invocation']=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':')).encode()).hexdigest();f.write_text(json.dumps(value));f.chmod(0o600);return phase.inputs(str(f),'attest')
   self.assertEqual(check(d)['identity_context'],'workshop')
   for key,value in [('identity_receipt_namespace','tenant-identity-writer'),('identity_receipt_name','portal-identity-evidence'),('identity_context_digest',c.derive('portal')['digest'])]:
    with self.assertRaises(ValueError):check({**d,key:value})
   missing=dict(d);missing.pop('identity_context_digest')
   with self.assertRaises(ValueError):check(missing)

if __name__=='__main__':unittest.main()
