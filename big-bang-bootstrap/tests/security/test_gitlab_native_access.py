import copy,importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'configuration/packages/gitlab/verification/native_access.py'
spec=importlib.util.spec_from_file_location('gitlab_native_access',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class NativeAccess(unittest.TestCase):
 def setUp(self):
  self.expected={'user_id':21,'group_id':31,'provider':'openid_connect','subject':'stable-subject','group_path':'tenants/example','access_level':30}
  self.user={'id':21,'is_admin':False,'state':'active','identities':[{'provider':'openid_connect','extern_uid':'stable-subject'}]}
  self.group={'id':31,'full_path':'tenants/example','visibility':'private'};self.member={'id':21,'access_level':30}
 def verify(self,**kw):
  args=dict(expected=self.expected,user=self.user,group=self.group,direct=self.member,effective=self.member,operation='enrolled');args.update(kw);return m.verify(**args)
 def test_explicit_approved_native_membership(self):self.assertTrue(self.verify()['native_group_access_verified'])
 def test_blocked_registration_is_not_enrollment(self):
  self.user['state']='blocked_pending_approval'
  with self.assertRaises(ValueError):self.verify()
 def test_subject_not_email_and_admin_denial(self):
  for change in ({'is_admin':True},{'identities':[{'provider':'openid_connect','extern_uid':'other-subject'}]},{'id':22}):
   user={**self.user,**change}
   with self.assertRaises(ValueError):self.verify(user=user)
 def test_cross_tenant_public_and_inherited_elevation_denied(self):
  for change in ({'full_path':'tenants/other'},{'id':32},{'visibility':'public'}):
   with self.assertRaises(ValueError):self.verify(group={**self.group,**change})
  with self.assertRaises(ValueError):self.verify(effective={'id':21,'access_level':50})
 def test_offboarding_requires_both_direct_and_effective_absence(self):
  for direct,effective in ((self.member,None),(None,self.member)):
   with self.assertRaises(ValueError):self.verify(direct=direct,effective=effective,operation='removed')
  result=self.verify(direct=None,effective=None,operation='removed');self.assertFalse(result['independent_credentials_revoked'])
 def test_ambiguous_input_and_provider_rejected(self):
  for change in ({'user_id':True},{'provider':'saml'},{'group_path':'platform/admins'},{'group_path':'tenants/example/subgroup'}):
   with self.assertRaises(ValueError):self.verify(expected={**self.expected,**change})
