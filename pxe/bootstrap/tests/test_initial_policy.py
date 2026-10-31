"""Execute rendered %post body against synthetic installed-root files only.

Host account/keys, ownership, SELinux, SSH/systemd are mocked. No chroot, sudo,
service, socket, package, credential creation or target node involved.
"""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest
from jinja2 import Environment,StrictUndefined
import yaml

ROOT=Path(__file__).resolve().parents[2]
ADAPTER=ROOT/'kickstart/bootstrap-post.ks.j2'

class InitialPolicy(unittest.TestCase):
    def run_post(self,failure='',missing=False,existing=False,export_state_to=None):
        with tempfile.TemporaryDirectory(prefix='perkforge-bootstrap-fixture-post-') as folder:
            root=Path(folder)
            for name in ['etc/ssh/sshd_config.d','etc/sudoers.d','home/bootstrap/.ssh','var/lib','bin']:
                (root/name).mkdir(parents=True,exist_ok=True)
            public='ssh-ed25519 AAAA fixture-only'
            key=root/'home/bootstrap/.ssh/authorized_keys';key.write_text(public+'\n')
            if failure=='missing-key':key.unlink()
            if failure=='wrong-key':key.write_text('ssh-ed25519 BBBB unrelated\n')
            if existing:
                (root/'var/lib/perkforge-bootstrap').mkdir()
                (root/'var/lib/perkforge-bootstrap/state.yml').write_text('preserve: original\n')
            events=root/'events';events.write_text('')
            mock=root/'bin/tool'
            mock.write_text('''#!/usr/bin/python3
from pathlib import Path
import json,os,subprocess,sys
name=Path(sys.argv[0]).name;args=sys.argv[1:];root=Path(os.environ['FIX_ROOT']);failure=os.environ['FIX_FAILURE']
with open(os.environ['FIX_EVENTS'],'a') as f:f.write(json.dumps([name,args])+"\\n")
if name=='getent':
 if failure=='missing-account':sys.exit(2)
 print('bootstrap:x:1000:1000::'+str(root/'home/bootstrap')+':/bin/bash');sys.exit(0)
if name=='chown':sys.exit(0)
if name=='install':
 clean=[];skip=False
 for arg in args:
  if skip:skip=False;continue
  if arg in ['-o','-g']:skip=True;continue
  if arg.startswith('-o') or arg.startswith('-g'):continue
  clean.append(arg)
 sys.exit(subprocess.call(['/usr/bin/install']+clean))
if name=='systemctl':
 assert args[0]=='--root=/'
 if args[1]=='enable' and failure=='enable':sys.exit(1)
 if args[1]=='enable':(root/'ssh-enabled').write_text('fixture marker only')
 if args[1]=='disable' and (root/'ssh-enabled').exists():(root/'ssh-enabled').unlink()
 sys.exit(0)
if name=='ssh-keygen':
 if args[0]=='-A':
  if failure=='hostkeys':sys.exit(1)
  (root/'etc/ssh/ssh_host_ed25519_key.pub').write_text('ssh-ed25519 CCCC SYNTHETIC_HOST_ONLY\\n');sys.exit(0)
 sys.exit(1 if failure=='invalid-public-key' else 0)
if name=='visudo':
 text=Path(args[-1]).read_text()
 sys.exit(1 if failure=='sudoers' or 'bootstrap ALL=(root) NOPASSWD: ALL' not in text else 0)
if name=='restorecon':sys.exit(1 if failure=='labels' else 0)
if name=='sshd':
 if args[0]=='-t':sys.exit(1 if failure=='syntax' else 0)
 text=(root/'etc/ssh/sshd_config.d/00-perkforge-bootstrap.conf').read_text()
 text='\\n'.join(x.lower() for x in text.splitlines() if x and not x.startswith('#'))
 if failure=='effective':text=text.replace('passwordauthentication no','passwordauthentication yes')
 if failure=='root-match' and 'user=root,' in args[-1]:text=text.replace('permitrootlogin no','permitrootlogin yes')
 print(text);sys.exit(0)
sys.exit(99)
''');mock.chmod(0o700)
            for name in ['getent','chown','install','systemctl','ssh-keygen','visudo','restorecon','sshd']:
                (root/'bin'/name).symlink_to(mock)
            env=Environment(undefined=StrictUndefined)
            values=dict(credential_mode='TEMPORARY_KEY_ONLY_BOOTSTRAP',bootstrap_username='bootstrap',
                bootstrap_public_key=public,bootstrap_controller_address='192.0.2.1',
                bootstrap_initial_ssh_policy=(ROOT/'bootstrap/templates/key-only.conf.j2').read_text(),
                bootstrap_initial_sudo_policy=env.from_string((ROOT/'bootstrap/templates/sudoers.j2').read_text()).render(bootstrap_user='bootstrap'))
            if missing:values['bootstrap_username']='UNCONFIGURED'
            rendered=env.from_string(ADAPTER.read_text()).render(**values)
            body=rendered.split('%post ',1)[1].split('\n',1)[1].split('\n%end',1)[0]
            # Root paths are substituted only in this test copy. Native command
            # paths become fixture tools; assert none can run on the host.
            for prefix in ['/etc/ssh','/etc/sudoers.d','/var/lib/perkforge-bootstrap','/etc/issue.d','/home/']:
                replacement=str(root/prefix.lstrip('/'))
                if prefix.endswith('/'):replacement+='/'
                body=body.replace(prefix,replacement)
            body=body.replace('/dev/console',str(root/'console'))
            for native in ['/usr/sbin/sshd','/usr/sbin/visudo','/usr/sbin/restorecon','/usr/bin/ssh-keygen','/usr/bin/systemctl','/usr/bin/getent']:
                body=body.replace(native,str(root/'bin'/Path(native).name))
            for native in ['systemctl','ssh-keygen','sshd','visudo','restorecon']:
                self.assertNotIn('/usr/bin/'+native,body)
                self.assertNotIn('/usr/sbin/'+native,body)
            script=root/'post.sh';script.write_text(body)
            syntax=subprocess.run(['bash','-n',str(script)],capture_output=True,text=True)
            self.assertEqual(syntax.returncode,0,syntax.stderr)
            result=subprocess.run(['bash',str(script)],capture_output=True,text=True,timeout=15,
                env={**os.environ,'PATH':str(root/'bin')+':/usr/bin:/bin','FIX_ROOT':str(root),'FIX_EVENTS':str(events),'FIX_FAILURE':failure})
            state=root/'var/lib/perkforge-bootstrap/state.yml'
            ssh=root/'etc/ssh/sshd_config.d/00-perkforge-bootstrap.conf';sudo=root/'etc/sudoers.d/90-perkforge-bootstrap'
            if export_state_to is not None and result.returncode==0:
                import shutil
                # Export only actual installed policy/account-key/ledger fixture
                # files into the following Ansible phase; never tool executables.
                for relative in ['etc/ssh/sshd_config.d/00-perkforge-bootstrap.conf',
                                 'etc/sudoers.d/90-perkforge-bootstrap',
                                 'home/bootstrap/.ssh/authorized_keys',
                                 'var/lib/perkforge-bootstrap/state.yml']:
                    source=root/relative;dest=Path(export_state_to)/relative
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,dest)
                (Path(export_state_to)/'var/lib/perkforge-bootstrap').chmod(0o700)
            return result,yaml.safe_load(state.read_text()) if state.exists() else {},[json.loads(x) for x in events.read_text().splitlines()],{
                'enabled':(root/'ssh-enabled').exists(),'ssh':ssh.read_text() if ssh.exists() else '',
                'sudo':sudo.read_text() if sudo.exists() else '',
                'ssh_mode':ssh.stat().st_mode&0o777 if ssh.exists() else None,
                'sudo_mode':sudo.stat().st_mode&0o777 if sudo.exists() else None,
                'state_mode':state.stat().st_mode&0o777 if state.exists() else None,
                'state_dir_mode':state.parent.stat().st_mode&0o777 if state.exists() else None}

    def test_success_writes_shared_policy_then_enables_only_offline(self):
        r,state,events,files=self.run_post()
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(state['access'],'outstanding_root_equivalent')
        self.assertEqual(state['result'],'configured_not_login_verified')
        self.assertTrue(files['enabled'])
        self.assertEqual(files['ssh_mode'],0o600);self.assertEqual(files['sudo_mode'],0o440)
        self.assertEqual(files['state_mode'],0o600);self.assertEqual(files['state_dir_mode'],0o700)
        self.assertEqual(files['ssh'],(ROOT/'bootstrap/templates/key-only.conf.j2').read_text())
        self.assertIn('bootstrap ALL=(root) NOPASSWD: ALL',files['sudo'])
        self.assertEqual(events[-1],['systemctl',['--root=/','enable','sshd.service']])
        self.assertIn(['ssh-keygen',['-A']],events) # mock invocation only, never real key generation
        for name,args in events:
            if name=='systemctl':self.assertNotIn('start',args);self.assertNotIn('restart',args)

    def test_unresolved_identity_never_reaches_file_or_tool_actions(self):
        r,state,events,files=self.run_post(missing=True)
        self.assertNotEqual(r.returncode,0);self.assertEqual(state,{})
        self.assertEqual(events,[]);self.assertFalse(files['enabled'])

    def test_missing_or_unexpected_anaconda_account_key_fails_before_grant(self):
        for failure in ['missing-account','missing-key','wrong-key','invalid-public-key']:
            with self.subTest(failure=failure):
                r,state,events,files=self.run_post(failure=failure)
                self.assertNotEqual(r.returncode,0)
                self.assertEqual(state,{})
                self.assertEqual(files['sudo'],'');self.assertFalse(files['enabled'])
                self.assertFalse(any(n=='systemctl' and 'enable' in a for n,a in events))

    def test_preserve_existing_ledger(self):
        r,state,events,files=self.run_post(existing=True)
        self.assertNotEqual(r.returncode,0);self.assertEqual(state,{'preserve':'original'})
        self.assertEqual(files['sudo'],'');self.assertFalse(files['enabled'])

    def test_failure_preserves_unknown_access_and_disables_ssh(self):
        for failure in ['sudoers','hostkeys','labels','syntax','effective','root-match','enable']:
            with self.subTest(failure=failure):
                r,state,events,files=self.run_post(failure=failure)
                self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
                self.assertEqual(state['access'],'outstanding_or_unknown')
                self.assertEqual(state['result'],'failed_requires_review')
                self.assertFalse(files['enabled'])
                self.assertEqual([e for e in events if e[0]=='systemctl'][-1],['systemctl',['--root=/','disable','sshd.service']])

if __name__=='__main__':unittest.main()
