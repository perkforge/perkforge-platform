"""Run the actual pre-activation task order offline with temporary ownership mocks.
The existing activate.yml is excluded: these tests never bind or start services.
"""
from pathlib import Path
import json,os,subprocess,sys,tempfile,unittest,yaml
ROOT=Path(__file__).resolve().parents[1] / 'transport'

class Handover(unittest.TestCase):
    def test_handover_and_refusals(self):
        scenarios=['success','approval','running','listener','guard','held','transaction','owner','mount','move-noop']
        for scenario in scenarios:
            with self.subTest(scenario=scenario),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                runtime=root/'run/perkforge-pxe-pilot';logs=root/'var/log/perkforge-pxe-pilot'
                (runtime/'config').mkdir(parents=True);logs.mkdir(parents=True)
                suffix='held-fixture-completed'
                if scenario=='held':Path(str(runtime)+'.'+suffix).mkdir()
                record=dict(config_dir='/wrong' if scenario=='transaction' else '/run/perkforge-pxe-pilot/config/session-fixture',units=['perkforge-pxe-pilot-dnsmasq.service','perkforge-pxe-pilot-http.service'],hashes={name:'a'*64 for name in ['dnsmasq.conf','grub.cfg','ingress.nft','nginx.conf']},lifetime_seconds=0)
                active=runtime/'config/active.json';active.write_text(json.dumps(record));active.chmod(0o600)
                mock=root/'mock.py'
                mock.write_text('''import sys,json,shutil
from pathlib import Path
root=Path(sys.argv[1]);scenario=sys.argv[2];cmd=sys.argv[3:]
with (root/'events').open('a') as out:out.write(json.dumps(cmd)+'\\n')
if cmd[:2]==['systemctl','show']:
 print('LoadState=loaded\\nActiveState=active\\nMainPID=123' if scenario=='running' else 'LoadState=not-found\\nActiveState=inactive\\nMainPID=0')
elif cmd[0]=='/usr/bin/ss':
 if scenario=='listener':print('udp UNCONN 0 0 192.0.2.1:69 0.0.0.0:*')
elif cmd[0]=='/usr/sbin/nft':print(json.dumps({'nftables':[{'table':{'family':'inet','name':'perkforge_pxe_pilot'}}] if scenario=='guard' else []}))
elif cmd[0]=='mountpoint':sys.exit(0 if scenario=='mount' else 32)
elif cmd[0]=='mv':
 if scenario!='move-noop':
  assert not Path(cmd[-1]).exists()
  shutil.move(cmd[-2],cmd[-1])
else:raise SystemExit('Unexpected mock command')
''')
                def mapped(text):
                    if isinstance(text,str) and text.startswith(('/run/perkforge-pxe-pilot','/var/log/perkforge-pxe-pilot')):return str(root)+text
                    return text
                play=yaml.safe_load((ROOT/'preserve-session.yml').read_text())[0]
                transformed=[]
                for task in play['tasks']:
                    if 'ansible.builtin.include_vars' in task:
                        if isinstance(task['ansible.builtin.include_vars'],str):
                            task={'ansible.builtin.set_fact':{'pilot_review_dir':'/tmp/perkforge-pxe-review-worker2-discovery-20261031'}}
                        else:task={'ansible.builtin.set_fact':{'previous_review':{'pilot_review_hashes':{name:'a'*64 for name in ['dnsmasq.conf','grub.cfg','ingress.nft','nginx.conf']},'pilot_lifetime_seconds':0}}}
                    for module,prop in [('ansible.builtin.stat','path'),('ansible.builtin.slurp','src')]:
                        if module in task:
                            task[module][prop]=mapped(task[module][prop])
                    if 'loop' in task and isinstance(task['loop'],list):task['loop']=[mapped(s) for s in task['loop']]
                    if 'ansible.builtin.command' in task:
                        cmd=task['ansible.builtin.command'];argv=cmd['argv'] if isinstance(cmd,dict) else cmd.split()
                        task['ansible.builtin.command']={'argv':[sys.executable,str(mock),str(root),scenario,*[mapped(x) for x in argv]]}
                    if 'ansible.builtin.assert' in task:
                        conditions=task['ansible.builtin.assert']['that']
                        if isinstance(conditions,str):conditions=[conditions]
                        task['ansible.builtin.assert']['that']=[x.replace('uid == 0','uid == fixture_uid') if isinstance(x,str) else x for x in conditions]
                    transformed.append(task)
                play['tasks']=transformed;play['become']=False;play.pop('vars_files',None)
                play['vars'].update(workspace_preservation_approved=scenario!='approval',workspace_previous_review_file='/tmp/fixture-review.yml',workspace_previous_config_dir='/run/perkforge-pxe-pilot/config/session-fixture',workspace_hold_label=suffix,fixture_uid=os.getuid()+int(scenario=='owner'),ansible_remote_tmp=str(root/'remote-tmp'))
                playfile=root/'play.yml';playfile.write_text(yaml.safe_dump([play]))
                result=subprocess.run(['ansible-playbook','-i','localhost,','-c','local',str(playfile)],capture_output=True,text=True,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local-tmp'),'ANSIBLE_REMOTE_TEMP':str(root/'remote-tmp')})
                self.assertEqual(result.returncode==0,scenario=='success',result.stdout+result.stderr)
                events=[json.loads(x) for x in (root/'events').read_text().splitlines()] if (root/'events').exists() else []
                moves=[e for e in events if e[0]=='mv']
                self.assertEqual(len(moves),2 if scenario in ('success','move-noop') else 0)
                if scenario=='success':
                    self.assertFalse(runtime.exists());self.assertFalse(logs.exists())
                    self.assertTrue(Path(str(runtime)+'.'+suffix+'/config/active.json').exists())
                elif scenario not in ('move-noop',):
                    self.assertTrue(active.exists());self.assertTrue(logs.exists())
                self.assertFalse(any(e[:2] in (['systemctl','stop'],['systemctl','reset-failed']) for e in events))
                if scenario=='approval':self.assertEqual(events,[])
                if scenario=='running':self.assertFalse(any(e[0]=='/usr/bin/ss' for e in events))
                if scenario=='listener':self.assertFalse(any(e[0]=='/usr/sbin/nft' for e in events))
                if scenario in ('held','transaction','owner','guard'):self.assertFalse(any(e[0]=='mountpoint' for e in events))
                if scenario=='mount':self.assertTrue(any(e[0]=='mountpoint' for e in events))

if __name__=='__main__':unittest.main()
