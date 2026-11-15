import importlib.util,json,os,subprocess,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SETUP=ROOT/'configuration/packages/gitlab/enrollment/setup'
spec=importlib.util.spec_from_file_location('bearer',SETUP/'operator-bearer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BearerTests(unittest.TestCase):
 def test_guards(self):
  with tempfile.TemporaryDirectory(prefix='kc-bearer-',dir=Path.home()) as tmp:
   p=Path(tmp)/'token'
   def write(value):p.write_text(json.dumps(value));p.chmod(0o600)
   write({'access_token':'synthetic-first-token','expires_at':1060});self.assertEqual(m.read_bearer(str(p),1000),'synthetic-first-token')
   for value in [{'access_token':'synthetic-first-token','expires_at':1015},{'access_token':'synthetic-first-token','expires_at':999},{'access_token':'synthetic-first-token','expires_at':99999},{'access_token':'bad\nvalue','expires_at':1060}]:
    write(value)
    with self.assertRaises(ValueError):m.read_bearer(str(p),1000)
   write({'access_token':'synthetic-first-token','expires_at':1060});p.chmod(0o644)
   with self.assertRaises(ValueError):m.read_bearer(str(p),1000)
 def test_actual_ansible_rereads_and_denies_expiry(self):
  with tempfile.TemporaryDirectory(prefix='kc-refresh-',dir=Path.home()) as tmp:
   t=Path(tmp);token=t/'token';token.write_text(json.dumps({'access_token':'synthetic-first-token','expires_at':time.time()+60}));token.chmod(0o600)
   play=t/'play.yaml'
   play.write_text('''- hosts: localhost
  connection: local
  gather_facts: false
  tasks:
  - ansible.builtin.assert:
      that: lookup('kc_operator_bearer', token) == 'synthetic-first-token'
  - ansible.builtin.copy:
      dest: '{{ token }}'
      mode: '0600'
      content: '{{ fresh | to_json }}'
  - ansible.builtin.assert:
      that: lookup('kc_operator_bearer', token) == 'synthetic-second-token'
''')
   env=dict(os.environ,ANSIBLE_LOOKUP_PLUGINS=str(SETUP/'lookup_plugins'))
   for expiry,expected in [(time.time()+60,0),(time.time()-1,2)]:
    token.write_text(json.dumps({'access_token':'synthetic-first-token','expires_at':time.time()+60}));token.chmod(0o600)
    p=subprocess.run(['ansible-playbook','-i','localhost,',str(play),'-e',json.dumps({'token':str(token),'fresh':{'access_token':'synthetic-second-token','expires_at':expiry}})],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    self.assertEqual(p.returncode,expected,p.stdout.decode()+p.stderr.decode())
if __name__=='__main__':unittest.main()
