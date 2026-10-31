"""Real Ansible task bodies; only temp files, mocked accounts/native tools/SSH.

Never creates users, credentials, listeners, VMs or services. Not a RHEL rehearsal.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import yaml

SOURCE=Path(__file__).resolve().parents[1]

class Components(unittest.TestCase):
    def run_flow(self, actions=('setup','handoff','revoke'), failure='', existing_account=False,
                 modify_grant=False, apply=True, initial_adapter=False, controller=False):
        with tempfile.TemporaryDirectory(prefix='perkforge-bootstrap-fixture-') as folder:
            root=Path(folder); role=root/'role'; shutil.copytree(SOURCE,role,ignore=shutil.ignore_patterns('tests','__pycache__'))
            # Replace ONLY account database effects with temp-file fixtures.
            # All other real task control flow/templates/file/command actions execute.
            def rewrite(tasks):
                for t in tasks:
                    if 'ansible.builtin.user' in t:
                        args=t.pop('ansible.builtin.user')
                        if failure=='controller-loss' and 'bootstrap_human_user' not in args['name']:
                            t['ansible.builtin.meta']='end_play'
                            continue
                        t['ansible.builtin.copy']={'dest':str(root/'accounts')+'/{{ '+('bootstrap_human_user' if 'bootstrap_human_user' in args['name'] else 'bootstrap_user')+' }}.json',
                            'content':json.dumps(args),'mode':'0600'}
                    if 'ansible.builtin.getent' in t:
                        args=t.pop('ansible.builtin.getent');key='operator' if 'bootstrap_human_user' in args['key'] else 'bootstrap'
                        t['ansible.builtin.set_fact']={'ansible_facts':{'getent_passwd':{key:'existing' if existing_account else None}}}
                    for key in ['ansible.builtin.file','ansible.builtin.copy','ansible.builtin.template']:
                        if key in t:
                            for field in ['owner','group']:
                                if field in t[key]:t[key][field]=str(os.getuid() if field=='owner' else os.getgid())
                    for key in ['block','rescue','always']:
                        if key in t:rewrite(t[key])
                return tasks
            for path in (role/'tasks').glob('*.yml'):
                path.write_text(yaml.safe_dump(rewrite(yaml.safe_load(path.read_text())),sort_keys=False))
            for directory in ['accounts','etc/ssh/sshd_config.d','etc/sudoers.d','home','bin']:
                (root/directory).mkdir(parents=True,exist_ok=True)
            if initial_adapter:
                from test_initial_policy import InitialPolicy
                post,_,_,_=InitialPolicy().run_post(export_state_to=root)
                self.assertEqual(post.returncode,0,post.stdout+post.stderr)
            events=root/'events.jsonl';events.write_text('')
            mock=root/'bin/tool'
            mock.write_text('''#!/usr/bin/python3
import os,sys,json
from pathlib import Path
name=Path(sys.argv[0]).name;args=sys.argv[1:];failure=os.environ.get('FIX_FAILURE','')
with open(os.environ['FIX_EVENTS'],'a') as f:f.write(json.dumps([name,args])+"\\n")
if name=='systemctl':

 if 'is-enabled' in args:
  print('enabled' if failure=='enabled-socket' else 'disabled');sys.exit(0 if failure=='enabled-socket' else 1)
 print('active' if failure=='active-service' else 'inactive');sys.exit(0 if failure=='active-service' else 3)
if name=='sshd':
 if '-t' in args:sys.exit(1 if failure=='syntax' else 0)
 print('pubkeyauthentication yes\\nauthenticationmethods publickey\\npasswordauthentication '+('yes' if failure=='effective' else 'no')+'\\nkbdinteractiveauthentication no\\npermitrootlogin '+('yes' if failure=='root-match' and 'user=root,' in args[-1] else 'no')+'\\nusepam yes\\nusedns no');sys.exit(0)
if name=='visudo':
 text=Path(args[-1]).read_text();sys.exit(1 if failure=='sudoers' or 'NOPASSWD: ALL' not in text else 0)
if name=='restorecon':sys.exit(0)
if name=='chpasswd':
 sys.stdin.read()
 sys.exit(1 if failure=='password-update' else 0)
if name=='ssh-keygen':
 if failure=='public-key':sys.exit(1)
 print('256 SHA256:DUMMY only-fixture (ED25519)');sys.exit(0)
if name in ['pkill','pgrep']:
 if name=='pgrep' and failure=='residual-process':print('12345');sys.exit(0)
 sys.exit(1)
if name=='ssh':
 user=args[args.index('-l')+1]
 if user=='bootstrap':
  if failure=='timeout':print('Connection timed out',file=sys.stderr);sys.exit(255)
  if Path(os.environ['FIX_ROOT']+'/home/bootstrap/.ssh/authorized_keys').exists():sys.exit(0)
  print('Permission denied (publickey).',file=sys.stderr);sys.exit(255)
 # Consume runtime secret without recording it anywhere.
 sys.stdin.read()
 if failure=='human-login':print('Permission denied',file=sys.stderr);sys.exit(255)
 if failure=='human-login-after':
  records=[json.loads(x) for x in Path(os.environ['FIX_EVENTS']).read_text().splitlines()]
  count=sum(1 for n,a in records if n=='ssh' and '-l' in a and a[a.index('-l')+1]=='operator')
  if count>1:print('Permission denied',file=sys.stderr);sys.exit(255)
 if failure=='passwordless':sys.exit(40)
 print('0');sys.exit(0)
sys.exit(99)
''');mock.chmod(0o700)
            for name in ['systemctl','sshd','visudo','restorecon','ssh','pkill','pgrep','ssh-keygen','chpasswd']:(root/'bin'/name).symlink_to(mock)
            variables=dict(bootstrap_component_apply=apply,bootstrap_root=str(root),bootstrap_user='bootstrap',
                bootstrap_human_user='operator',bootstrap_public_key='ssh-ed25519 AAAA fixture-only',
                bootstrap_human_public_key='ssh-ed25519 BBBB fixture-only',
                bootstrap_human_sudo_password='DUMMY_RUNTIME_ONLY',bootstrap_controller_address='192.0.2.1',
                bootstrap_target_host='fixture.invalid',bootstrap_known_hosts_file=str(root/'known_hosts'),
                bootstrap_identity_file=str(root/'bootstrap-key-reference'),bootstrap_human_identity_file=str(root/'human-key-reference'),
                bootstrap_timeout='/usr/bin/timeout',bootstrap_uid=str(os.getuid()),bootstrap_gid=str(os.getgid()),bootstrap_owner_uid=os.getuid())
            for name in ['systemctl','sshd','visudo','restorecon','ssh','pkill','pgrep','ssh-keygen','chpasswd']:variables['bootstrap_'+name.replace('-','_')]=str(root/'bin'/name)
            tasks=[]
            for action in actions:
                if action=='revoke' and modify_grant:
                    tasks.append({'ansible.builtin.copy':{'dest':str(root/'etc/sudoers.d/90-perkforge-bootstrap'),'content':'UNRELATED GRANT\n'}})
                tasks.append({'ansible.builtin.include_role':{'name':str(role)},'vars':{'bootstrap_action':action}})
            if controller:
                variables['bootstrap_handoff_apply']=apply
                variables['bootstrap_public_key_file']=str(root/'bootstrap.pub')
                variables['bootstrap_human_public_key_file']=str(root/'human.pub')
                for name,content in [('bootstrap.pub',variables['bootstrap_public_key']),('human.pub',variables['bootstrap_human_public_key']),
                                     ('known_hosts','fixture.invalid ssh-ed25519 AAAA'),('bootstrap-key-reference','FIXTURE_NOT_A_KEY'),('human-key-reference','FIXTURE_NOT_A_KEY')]:
                    p=root/name;p.write_text(content+'\n');p.chmod(0o600)
                controller_plays=yaml.safe_load((role/'handoff.yml').read_text())
                for play_data in controller_plays:
                    for t in play_data.get('tasks',[]):
                        if 'ansible.builtin.pause' in t:
                            t.pop('ansible.builtin.pause');registered=t.pop('register',None)
                            t['ansible.builtin.set_fact']={registered:{'user_input':'DUMMY_RUNTIME_ONLY'}}
                        if 'ansible.builtin.add_host' in t:
                            t['ansible.builtin.add_host']['ansible_connection']='local'
                            t['ansible.builtin.add_host']['ansible_become']=False
                play=role/'handoff.yml';play.write_text(yaml.safe_dump(controller_plays,sort_keys=False))
                values_file=root/'controller-inputs.yml';values_file.write_text(yaml.safe_dump(variables));values_file.chmod(0o600)
                args=['ansible-playbook','-i','localhost,','-c','local',str(play),'-e','@'+str(values_file)]
            else:
                play=root/'test.yml';play.write_text(yaml.safe_dump([dict(hosts='localhost',connection='local',gather_facts=False,vars=variables,tasks=tasks)],sort_keys=False))
                args=['ansible-playbook','-i','localhost,','-c','local',str(play)]
            env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'ansible-local'),'ANSIBLE_REMOTE_TEMP':str(root/'ansible-remote'),
                'FIX_ROOT':str(root),'FIX_FAILURE':failure,'FIX_EVENTS':str(events)}
            result=subprocess.run(args,env=env,capture_output=True,text=True,timeout=60)
            ledger=root/'var/lib/perkforge-bootstrap/state.yml'
            state=yaml.safe_load(ledger.read_text()) if ledger.exists() else {}
            return result,state,[json.loads(x) for x in events.read_text().splitlines()],{
                'bootstrap_key':(root/'home/bootstrap/.ssh/authorized_keys').exists(),
                'sudo_grant':(root/'etc/sudoers.d/90-perkforge-bootstrap').exists(),
                'human_key':(root/'home/operator/.ssh/authorized_keys').exists(),
                'account_files':[p.name for p in (root/'accounts').iterdir()],
                'state_mode':ledger.stat().st_mode&0o777 if ledger.exists() else None}

    def test_complete_setup_handoff_revoke_positive_path(self):
        r,state,events,files=self.run_flow()
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(state['access'],'revoked')
        self.assertFalse(files['bootstrap_key']);self.assertFalse(files['sudo_grant']);self.assertTrue(files['human_key'])
        self.assertEqual(files['state_mode'],0o600)
        ssh=[e[1] for e in events if e[0]=='ssh'];self.assertEqual(len(ssh),3)
        for args in ssh:
            self.assertIn('StrictHostKeyChecking=yes',args);self.assertIn('ControlPath=none',args)
            self.assertNotIn('DUMMY_RUNTIME_ONLY',' '.join(args))
        self.assertNotIn('DUMMY_RUNTIME_ONLY',r.stdout+r.stderr)
        self.assertNotIn('DUMMY$NOT_A_REAL_HASH',r.stdout+r.stderr)
        self.assertFalse(any('start' in args or 'reload' in args for name,args in events if name=='systemctl'))

    def test_kickstart_adapter_to_human_handoff_and_revocation(self):
        r,state,events,files=self.run_flow(actions=('handoff','revoke'),initial_adapter=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(state['access'],'revoked')
        self.assertFalse(files['bootstrap_key']);self.assertFalse(files['sudo_grant'])
        self.assertTrue(files['human_key'])

    def test_controller_caller_transitions_alias_then_revokes(self):
        r,state,events,files=self.run_flow(initial_adapter=True,controller=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(state['access'],'revoked')
        self.assertTrue(files['human_key']);self.assertFalse(files['bootstrap_key'])
        self.assertIn('Human key/password-sudo verified',r.stdout)
        self.assertNotIn('DUMMY_RUNTIME_ONLY',r.stdout+r.stderr)

    def test_controller_default_gate_reads_no_keys_or_passwords(self):
        r,state,events,files=self.run_flow(controller=True,apply=False)
        self.assertNotEqual(r.returncode,0);self.assertEqual(state,{})
        self.assertEqual(events,[]);self.assertEqual(files['account_files'],[])
        self.assertNotIn('Enter approved human account password',r.stdout)

    def test_failed_password_update_preserves_bootstrap(self):
        r,state,events,files=self.run_flow(initial_adapter=True,controller=True,failure='password-update')
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(state['access'],'outstanding_or_unknown')
        self.assertTrue(files['bootstrap_key']);self.assertTrue(files['sudo_grant'])
        self.assertNotIn('DUMMY_RUNTIME_ONLY',r.stdout+r.stderr)

    def test_failed_setup_accounts_for_possible_access(self):
        for failure in ['active-service','enabled-socket','public-key','sudoers','syntax','effective','root-match']:
            with self.subTest(failure=failure):
                r,state,events,files=self.run_flow(actions=('setup',),failure=failure)
                self.assertNotEqual(r.returncode,0)
                self.assertEqual(state['access'],'outstanding_or_unknown')
                self.assertEqual(state['result'],'failed_requires_review')
                expected={'active-service':'systemctl','enabled-socket':'systemctl','sudoers':'visudo','syntax':'sshd','effective':'sshd','root-match':'sshd','public-key':'ssh-keygen'}[failure]
                self.assertTrue(any(name==expected for name,args in events))
                self.assertFalse(any(e[0]=='ssh' for e in events))

    def test_unverified_human_never_revokes_recovery_access(self):
        for failure in ['human-login','passwordless']:
            with self.subTest(failure=failure):
                r,state,events,files=self.run_flow(failure=failure)
                self.assertTrue(any(n=='ssh' and 'operator' in a for n,a in events))
                self.assertNotEqual(r.returncode,0)
                self.assertEqual(state['access'],'outstanding_or_unknown')
                self.assertTrue(files['bootstrap_key']);self.assertTrue(files['sudo_grant'])

    def test_timeout_is_not_bootstrap_revocation_proof(self):
        r,state,_,_=self.run_flow(failure='timeout')
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(state['access'],'outstanding_or_unknown')

    def test_human_failure_after_removal_is_not_reported_success(self):
        r,state,events,files=self.run_flow(failure='human-login-after')
        self.assertNotEqual(r.returncode,0)
        self.assertFalse(files['bootstrap_key']);self.assertFalse(files['sudo_grant'])
        self.assertEqual(state['access'],'outstanding_or_unknown')
        self.assertEqual(state['result'],'failed_requires_review')

    def test_controller_interruption_retains_intent_ledger(self):
        r,state,events,files=self.run_flow(actions=('setup',),failure='controller-loss')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(state['access'],'outstanding_or_unknown')
        self.assertEqual(state['result'],'in_progress')
        self.assertEqual(files['account_files'],[])

    def test_remote_sudo_command_checks_password_requirement_without_argument_secret(self):
        # Execute the actual rendered remote shell expression with a fixture sudo,
        # not a real sudo invocation. This catches quoting/errexit regressions.
        r,_,events,_=self.run_flow()
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        command=next(a[-1] for n,a in events if n=='ssh' and 'operator' in a)
        with tempfile.TemporaryDirectory(prefix='perkforge-bootstrap-fixture-') as folder:
            p=Path(folder)/'sudo'
            p.write_text('#!/bin/bash\ncase "$1" in\n-k) exit 0;;\n-n) exit "${FIX_REQUIRE_PASSWORD:-1}";;\n-S) read -r dummy; [[ $dummy == DUMMY_RUNTIME_ONLY ]] || exit 42; printf "0\\n";;\n*) exit 99;;\nesac\n')
            p.chmod(0o700)
            env={**os.environ,'PATH':folder+':/usr/bin:/bin'}
            good=subprocess.run(['bash','-c',command],input='DUMMY_RUNTIME_ONLY\n',text=True,capture_output=True,env=env)
            self.assertEqual(good.returncode,0,good.stderr);self.assertEqual(good.stdout.strip(),'0')
            bad=subprocess.run(['bash','-c',command],input='DUMMY_RUNTIME_ONLY\n',text=True,capture_output=True,env={**env,'FIX_REQUIRE_PASSWORD':'0'})
            self.assertEqual(bad.returncode,40)

    def test_residual_bootstrap_process_keeps_access_unknown(self):
        r,state,_,_=self.run_flow(failure='residual-process')
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(state['access'],'outstanding_or_unknown')

    def test_modified_sudo_grant_is_not_deleted(self):
        r,state,_,files=self.run_flow(modify_grant=True)
        self.assertNotEqual(r.returncode,0)
        self.assertTrue(files['sudo_grant']);self.assertTrue(files['bootstrap_key'])
        self.assertEqual(state['access'],'outstanding_or_unknown')

    def test_default_gate_has_no_account_or_command_effects(self):
        r,state,events,files=self.run_flow(actions=('setup',),apply=False)
        self.assertNotEqual(r.returncode,0);self.assertEqual(state,{})
        self.assertEqual(events,[]);self.assertEqual(files['account_files'],[])

    def test_existing_account_preserved(self):
        r,state,events,files=self.run_flow(actions=('setup',),existing_account=True)
        self.assertNotEqual(r.returncode,0);self.assertEqual(files['account_files'],[])
        self.assertEqual(state['access'],'outstanding_or_unknown')

if __name__=='__main__':unittest.main()
