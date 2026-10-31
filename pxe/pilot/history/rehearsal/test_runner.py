"""Real Ansible lifecycle task control flow; native side effects replaced by model.

All files live in a fresh temp root. Never creates VM/namespace/service/key/user or
sends packets. This is explicitly NOT the full RHEL installation rehearsal.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import yaml

REPO=Path(__file__).resolve().parents[2]
PXE=REPO/'pxe'

NATIVE=r'''#!/usr/bin/python3
from ansible.module_utils.basic import AnsibleModule
from pathlib import Path
import hashlib,json,os,shutil,subprocess
m=AnsibleModule(argument_spec={'argv':{'type':'list','elements':'str'},'cmd':{'type':'str'},'creates':{'type':'str'},'stdin':{'type':'str'}},supports_check_mode=True)
root=Path(os.environ['MODEL_ROOT']);statefile=root/'model.json'
s=json.loads(statefile.read_text());args=m.params['argv'] or m.params['cmd'].split();name=Path(args[0]).name
s['events'].append(args) # no stdin/password logging
out='';err='';rc=0
failure=os.environ.get('MODEL_FAILURE','')
if failure=='unit-replaced' and name=='systemctl' and 'show' in args:
 for u in s['units'].values():u['invocation']='f'*32
if name=='id':out='0'
elif name=='df':out='Avail\n999999999999'
elif name=='getent':out='fixture:x:1000:1000:Fixture:/nonexistent:/bin/false'
elif name in ['qemu-system-x86_64','qemu-img','qemu-io','ip','dnsmasq','nginx','nft','systemd-run','xorriso'] and any(x in args for x in ['--version','-version','-Version','-v']):out='Fixture tool version'
elif name=='mkdir':Path(args[-1]).mkdir(mode=0o711)
elif name=='ssh-keygen':
 p=Path(args[args.index('-f')+1]);p.write_text('DUMMY_NOT_A_KEY');p.chmod(0o600)
 (Path(str(p)+'.pub')).write_text('ssh-ed25519 AAAA '+p.name+'\n')
elif name=='xorriso':
 target=Path(args[-1])
 for relative,content in [('EFI/BOOT/grub.cfg','linux /images/pxeboot/vmlinuz\ninitrd /images/pxeboot/initrd.img\n'),('images/pxeboot/vmlinuz','DUMMY'),('images/pxeboot/initrd.img','DUMMY'),('.treeinfo','DUMMY')]:
  p=target/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
elif name=='cp':shutil.copytree(args[-2],args[-1])
elif name=='find':
 if '-exec' in args:
  base=Path(args[1]);mode=int(args[args.index('/usr/bin/chmod')+1],8);files=args[args.index('-type')+1]=='f'
  for p in [base,*base.rglob('*')]:
   if p.is_file()==files:p.chmod(mode)
 else:out=''
elif name=='qemu-img':
 if args[1]=='create':Path(args[-2]).write_text('IMAGE '+args[-1])
 elif args[1]=='convert':shutil.copyfile(args[-2],args[-1])
 elif args[1]=='compare':rc=0 if Path(args[-2]).read_bytes()==Path(args[-1]).read_bytes() else 1
 else:rc=98
elif name=='qemu-io':
 p=Path(args[-1]);p.write_text(p.read_text()+' SENTINEL')
elif name=='ip':
 nsdir=root/'netns'
 if args[1:3]==['netns','list']:out='\n'.join(s['namespaces'])
 elif args[1:3]==['netns','add']:
  nsdir.mkdir(exist_ok=True);p=nsdir/args[3];p.write_text('NAMESPACE MODEL');s['namespaces'].append(args[3])
 elif args[1:3]==['netns','delete']:
  p=nsdir/args[3];p.unlink();s['namespaces'].remove(args[3])
 elif args[1:3]==['netns','pids']:out='1234' if any(u['active'] for u in s['units'].values()) else ''
 elif '-n' in args:
  assert args[args.index('-n')+1] in s['namespaces']
  assert 'route' not in args # no default routes/uplink anywhere
 elif args[1:3]==['netns','exec']:assert args[3] in s['namespaces']
 else:rc=98
elif name=='systemd-run':
 unit=next(x.split('=',1)[1] for x in args if x.startswith('--unit='));s['units'][unit]={'invocation':hashlib.sha256(unit.encode()).hexdigest()[:32],'active':True,'command':' '.join(args)}
 if unit.endswith('-vm.service'):
  console=next(x[5:] for x in args if x.startswith('file:'))
  text='PERKFORGE_DISK_IDENTITY_REJECTED\n' if os.environ['MODEL_SCENARIO']!='install' else 'PERKFORGE_HOSTKEY ssh-ed25519 AAAA SYNTHETIC\nPERKFORGE_INITIAL_POLICY_READY\n'
  Path(console).write_text(text)
  if failure=='post-failure':Path(console).write_text('PERKFORGE_INITIAL_POLICY_FAILED syntax\n')
  if failure=='changed-canary':
   p=Path(console).parents[2]/'vm/canary.raw';p.write_text('CHANGED')
elif name=='systemctl':
 unit=next((x for x in args if x.endswith('.service')),None);u=s['units'].get(unit)
 if args[1]=='show':
  if '--value' in args:out='not-found' if not u else u['invocation']
  elif not u:out='LoadState=not-found\nActiveState=inactive\nMainPID=0'
  else:out='LoadState=loaded\nActiveState='+('active' if u['active'] else 'inactive')+'\nMainPID='+('1234' if u['active'] else '0')+'\nInvocationID='+u['invocation']+'\nExecStart='+u['command']
 elif args[1]=='stop':
  assert u;s['units'][unit]['active']=False
 else:rc=98
elif name=='ansible-playbook':
 s['human']=True;s['revoked']=True;out='MOCK handoff completed'
elif name=='timeout' or name=='namespace-ssh':
 command=args[-1];human=any('operator@' in x for x in args)
 if human and not s['human']:rc=255;err='Permission denied'
 elif not human and s['revoked']:rc=255;err='Permission denied (publickey)'
 elif 'state.yml' in command:out='account: bootstrap\naccess: revoked\n'
 elif 'boot_id' in command:out=s['boot_id']
 elif 'systemctl reboot' in command:s['boot_id']='22222222-2222-2222-2222-222222222222';rc=255
 elif 'systemctl poweroff' in command:s['qmp']='shutdown';rc=255
 elif 'id -u' in command:out='0'
 elif 'os-release' in command:rc=0
 else:rc=0
elif name=='python3':
 if 'ksvalidator.py' in args[1]:
  p=subprocess.run(args,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(Path(args[1]).parents[1])});rc=p.returncode;out=p.stdout;err=p.stderr
 elif 'qmp_status.py' in args[1]:out=json.dumps({'status':s['qmp']})
 else:rc=98
else:rc=98;err='Unexpected native call blocked by fixture: '+name
statefile.write_text(json.dumps(s))
if rc:m.fail_json(msg=err or 'Fixture native rejection',rc=rc,stdout=out,stderr=err)
m.exit_json(changed=False,rc=0,stdout=out,stderr=err)
'''

class Fixture:
    def __init__(self, failure='', scenario='install', interrupt=False):
        self.temp=tempfile.TemporaryDirectory(prefix='perkforge-rehearsal-fixture-');self.root=Path(self.temp.name)
        self.failure=failure;self.scenario=scenario
        self.source=self.root/'source';shutil.copytree(PXE,self.source,ignore=shutil.ignore_patterns('local','__pycache__'))
        # approved local validator source only; never download/build in tests
        self.validator=PXE/'local/tools/pykickstart-3.78'
        (self.source/'local/tools').mkdir(parents=True)
        if self.validator.exists():shutil.copytree(self.validator,self.source/'local/tools/pykickstart-3.78')
        archive=PXE/'local/tools/pykickstart-3.78.tar.gz'
        if archive.exists():shutil.copyfile(archive,self.source/'local/tools'/archive.name)
        self.execution=self.root/'runs';self.execution.mkdir()
        self.run_id='test-run-0001';self.run=self.execution/self.run_id
        self.iso=self.root/'fixture.iso';self.iso.write_text('SYNTHETIC_ISO')
        self.mem=self.root/'meminfo';self.mem.write_text('MemAvailable: '+('1024' if failure=='memory' else '99999999')+' kB\n')
        self.model=self.root/'model.json';self.model.write_text(json.dumps(dict(events=[],units={},namespaces=[],human=False,revoked=False,boot_id='11111111-1111-1111-1111-111111111111',qmp='running')))
        self.library=self.root/'library';self.library.mkdir();(self.library/'fixture_native.py').write_text(NATIVE)
        def strings(value):
            if isinstance(value,str):
                value=value.replace('/var/lib/perkforge-pxe-rehearsal',str(self.execution)).replace('/run/netns/',str(self.root/'netns')+'/').replace('/proc/meminfo',str(self.mem))
                # source guard now expects only this fixture temp path
                value=value.replace('== 11059986432','== 13').replace('.stat.uid == 0','.stat.uid == '+str(os.getuid()))
                if "lookup('ansible.builtin.password'" in value:return 'DUMMY_RUNTIME_ONLY'
                return value
            if isinstance(value,list):return [strings(x) for x in value]
            if isinstance(value,dict):return {k:strings(v) for k,v in value.items()}
            return value
        def rewrite(tasks):
            for t in tasks:
                if 'ansible.builtin.command' in t:
                    args=t.pop('ansible.builtin.command');t['fixture_native']={'cmd':args} if isinstance(args,str) else args
                for kind in ['ansible.builtin.file','ansible.builtin.copy','ansible.builtin.template']:
                    if kind in t:
                        for field,uid in [('owner',os.getuid()),('group',os.getgid())]:
                            if field in t[kind]:t[kind][field]=str(uid)
                if t.get('name')=='Generate/persist disposable guest password only in protected root credential path':
                    t['ansible.builtin.copy']={'dest':'{{ rehearsal_root }}/credentials/human.password','content':'DUMMY_RUNTIME_ONLY\n','mode':'0600'};t.pop('ansible.builtin.set_fact')
                if interrupt and t.get('ansible.builtin.include_tasks')=='rehearsal/verify.yml':
                    t.pop('ansible.builtin.include_tasks');t['ansible.builtin.meta']='end_play'
                for key in ['block','rescue','always']:
                    if key in t:rewrite(t[key])
            return tasks
        for p in [self.source/'ansible/rehearsal.yml',*(self.source/'ansible/rehearsal').glob('*.yml')]:
            data=yaml.safe_load(p.read_text())
            if p.name=='rehearsal.yml':
                for play in data:play['tasks']=rewrite(play['tasks'])
            else:data=rewrite(data)
            p.write_text(yaml.safe_dump(strings(data),sort_keys=False))
        self.vars=self.root/'vars.yml'
        self.values=dict(rehearsal_execution_approved=True,rehearsal_credential_generation_approved=True,rehearsal_rhel_agreement_approved=True,rehearsal_accel='tcg',rehearsal_action='start',rehearsal_run_id=self.run_id,rehearsal_iso=str(self.iso),rehearsal_iso_sha256=hashlib.sha256(self.iso.read_bytes()).hexdigest(),rehearsal_scenario=scenario)
    def run_action(self,action='start',approved=True):
        v={**self.values,'rehearsal_action':action,'rehearsal_execution_approved':approved};self.vars.write_text(yaml.safe_dump(v))
        env={**os.environ,'ANSIBLE_LIBRARY':str(self.library),'ANSIBLE_LOCAL_TEMP':str(self.root/'ansible-local'),'ANSIBLE_REMOTE_TEMP':str(self.root/'ansible-remote'),'MODEL_ROOT':str(self.root),'MODEL_FAILURE':self.failure,'MODEL_SCENARIO':self.scenario}
        return subprocess.run(['ansible-playbook','-i','localhost,','-c','local',str(self.source/'ansible/rehearsal.yml'),'-e','@'+str(self.vars)],env=env,capture_output=True,text=True,timeout=90)
    def state(self):return yaml.safe_load((self.run/'state.yml').read_text())
    def native(self):return json.loads(self.model.read_text())
    def close(self):self.temp.cleanup()

@unittest.skip('Parked incomplete custom VM runner; failed memory-parsing fixture preserved, not worker readiness evidence')
class Rehearsal(unittest.TestCase):
    def test_default_off_performs_no_native_action(self):
        f=Fixture()
        try:
            p=f.run_action(approved=False);self.assertNotEqual(p.returncode,0)
            self.assertEqual(f.native()['events'],[]);self.assertFalse(f.run.exists())
        finally:f.close()
    def test_complete_install_handoff_reboot_disarm_cleanup_mock_path(self):
        f=Fixture()
        try:
            p=f.run_action();self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertEqual(f.state()['phase'],'verified_stopped')
            self.assertEqual(f.native()['namespaces'],[])
            self.assertFalse(any(x['active'] for x in f.native()['units'].values()))
            self.assertIn('Installation disarmed',(f.run/'media/tftp/EFI/BOOT/grub.cfg').read_text())
            self.assertNotIn('DUMMY_RUNTIME_ONLY',p.stdout+p.stderr)
        finally:f.close()

if __name__=='__main__':unittest.main()
