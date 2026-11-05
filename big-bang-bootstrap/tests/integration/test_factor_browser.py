"""Offline protocol safety/math tests; not live factor acceptance evidence."""
import base64,importlib.util,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('factor_browser',ROOT/'configuration/authorization/files/verify-factor-browser.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FactorBrowser(unittest.TestCase):
 def test_rfc6238_public_sha1_vector(self):
  key=base64.b32encode(b'12345678901234567890').decode()
  self.assertEqual(m.otp(key,{'algorithm':'HmacSHA1','digits':8,'period':30},1),'94287082')
 def test_pinned_form_fields_and_escaped_action(self):
  p=m.Forms('<form id="kc-totp-settings-form" action="/action?a=1&amp;b=2"><input type="hidden" name="totpSecret" value="synthetic-only"><input name="totp"></form><a id="mode-manual" href="/manual">manual</a><span id="kc-totp-secret-key">ABCD EFGH</span><span id="input-error-otp-code">invalid</span>')
  self.assertEqual(p.forms['kc-totp-settings-form']['action'],'/action?a=1&b=2');self.assertEqual(p.forms['kc-totp-settings-form']['hidden'],{'totpSecret':'synthetic-only'});self.assertEqual(p.secrets['kc-totp-secret-key'],'ABCD EFGH');self.assertIn('input-error-otp-code',p.ids)
 def test_redirect_cannot_send_forms_to_another_origin(self):
  response=Mock(status_code=302,headers={'Location':'https://elsewhere.invalid/'})
  session=Mock();session.request.return_value=response
  with patch.object(m.requests,'Session',return_value=session):
   b=m.Browser({'url':'https://identity.invalid/auth','ca':'public-ca','redirect':'https://identity.invalid/account/'})
   with self.assertRaises(m.Stop):b.fetch('https://identity.invalid/auth','POST',{'password':'synthetic-only'})
   self.assertEqual(session.request.call_count,1)
 def test_state_mismatch_refuses_token_exchange(self):
  with patch.object(m.requests,'Session') as session:
   b=m.Browser({'url':'https://identity.invalid/auth','ca':'public-ca','redirect':'https://identity.invalid/account/'});b.callback={'state':['foreign'],'code':['synthetic-code']}
   with self.assertRaises(m.Stop):b.token()
   session.return_value.post.assert_not_called()
 def test_default_and_check_mode_contact_no_live_service(self):
  with tempfile.TemporaryDirectory() as d:
   env={**os.environ,'ANSIBLE_LOCAL_TEMP':d+'/local','ANSIBLE_REMOTE_TEMP':d+'/remote'}
   for args in [[],['-e','factor_apply=true','--check']]:
    r=subprocess.run(['ansible-playbook','-i',str(ROOT/'configuration/ansible/inventory.yaml'),str(ROOT/'configuration/authorization/factor-acceptance.yaml')]+args,env=env,capture_output=True,text=True,timeout=30)
    self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
