"""Offline activation/shutdown guards; external commands are temporary-file mocks."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]

class ActivationTests(unittest.TestCase):
    def test_activation_guard_order_and_narrow_mutations(self):
        play=yaml.safe_load((ROOT/'activate.yml').read_text())[0]
        self.assertFalse(play['vars']['pilot_activation_approved'])
        block=play['tasks'][-1]['block']
        apply=next(i for i,t in enumerate(block) if 'Apply only dedicated' in t.get('name',''))
        listen=next(i for i,t in enumerate(block) if 'Validate final nginx' in t.get('name',''))
        launch=next(i for i,t in enumerate(block) if 'Launch bounded' in t.get('name',''))
        self.assertLess(apply,listen)
        self.assertLess(listen,launch)
        self.assertIn('rescue',play['tasks'][-1])
        self.assertEqual(block[apply]['ansible.builtin.command']['argv'][:2],['/usr/sbin/nft','-f'])
        self.assertTrue(block[apply]['ansible.builtin.command']['argv'][-1].endswith('/apply-guard.nft'))
        placement=(ROOT/'activation-placement.yml').read_text()
        self.assertIn('create table inet perkforge_pxe_pilot',placement)
        self.assertIn('verify-activation-copies.yml',placement)
        self.assertIn("mode: '0444'",placement)
        for forbidden in ('killall','pkill','flush ruleset','masked: false','state: started'):
            # Comments mentioning a forbidden command are not executable actions.
            self.assertNotIn(forbidden,(ROOT/'activate.yml').read_text())
        self.assertIn('RuntimeMaxSec=',(ROOT/'activate.yml').read_text())

    def test_shutdown_mocks_success_identity_collision_guard_change_and_residual(self):
        for scenario in ('normal','already-stopped','unit-mismatch','invocation-mismatch','guard-mismatch','listener-remains'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                config='/run/perkforge-pxe-pilot/config/session-fixture'
                units=['perkforge-pxe-pilot-dnsmasq.service','perkforge-pxe-pilot-http.service']
                baseline='1 system-dnsmasq\n2 libvirt-dnsmasq'
                canonical=json.dumps({'nftables':[{'table':{'family':'inet','name':'perkforge_pxe_pilot'}}]})
                record=dict(config_dir=config,units=units,dnsmasq_baseline=baseline)
                if scenario!='already-stopped': (root/'guard').write_text('present')
                mock=root/'mock.py'
                mock.write_text(r'''import json,sys
from pathlib import Path
root=Path(sys.argv[1]); scenario=sys.argv[2]; cmd=sys.argv[3:]
with (root/'events').open('a') as f:f.write(json.dumps(cmd)+'\n')
if cmd[:2]==['systemctl','show']:
 if cmd[2]=='nginx.service':print('LoadState=masked\nActiveState=inactive')
 elif 'ExecStart' in cmd and scenario=='already-stopped':print('LoadState=not-found')
 elif 'ExecStart' in cmd:
  print('LoadState=loaded\nExecStart=/usr/sbin/dnsmasq '+('/other' if scenario=='unit-mismatch' else '/run/perkforge-pxe-pilot/config/session-fixture')+'/dnsmasq.conf\nInvocationID='+'1'*32+'\nMainPID=123\nKillMode=control-group')
 else:print('MainPID=0\nActiveState=inactive')
elif cmd[:2]==['systemctl','stop']:pass
elif cmd[0]=='/usr/bin/ss':
 if scenario=='listener-remains':print('udp UNCONN 0 0 192.0.2.10:69 0.0.0.0:*')
elif cmd[0]=='ps':print('1 system-dnsmasq\n2 libvirt-dnsmasq')
elif cmd[:4]==['/usr/sbin/nft','-j','list','tables']:
 print(json.dumps({'nftables':[{'table':{'family':'inet','name':'perkforge_pxe_pilot'}}] if (root/'guard').exists() else []}))
elif cmd[:4]==['/usr/sbin/nft','-j','list','table']:
 print(json.dumps({'nftables':[{'table':{'family':'inet','name':'perkforge_pxe_pilot'}}]} if scenario!='guard-mismatch' else {'changed':True}))
elif cmd[:3]==['/usr/sbin/nft','delete','table']:(root/'guard').unlink()
else:raise SystemExit('Unexpected command '+repr(cmd))
''')
                tasks=yaml.safe_load((ROOT/'shutdown-tasks.yml').read_text())
                def transform(items):
                    out=[]
                    for task in items:
                        task=dict(task)
                        if 'ansible.builtin.include_tasks' in task:
                            out.extend(transform(yaml.safe_load((ROOT/task['ansible.builtin.include_tasks']).read_text())))
                            continue
                        if 'ansible.builtin.stat' in task or 'ansible.builtin.slurp' in task:
                            continue
                        if 'ansible.builtin.command' in task:
                            command=task['ansible.builtin.command']
                            argv=command['argv'] if isinstance(command,dict) else command.split()
                            task['ansible.builtin.command']={'argv':[sys.executable,str(mock),str(root),scenario,*argv]}
                        if 'block' in task:
                            task['block']=transform(task['block'])
                        out.append(task)
                    return out
                variables=dict(pilot_runtime='/run/perkforge-pxe-pilot',pilot_logs='/var/log/perkforge-pxe-pilot',pilot_units=units,
                    active_record={'stat':{'isreg':True,'islnk':False,'uid':0,'mode':'0600'}},
                    active_data={'content':base64.b64encode(json.dumps(record).encode()).decode()},
                    identity_file={'stat':{'exists':scenario=='invocation-mismatch','isreg':True,'islnk':False,'uid':0,'mode':'0600'}},
                    identity_data={'content':base64.b64encode(json.dumps(['InvocationID='+'0'*32]*2).encode()).decode()},
                    recorded_guard={'content':base64.b64encode(canonical.encode()).decode()})
                play=root/'play.yml'
                play.write_text(yaml.safe_dump([dict(hosts='localhost',connection='local',gather_facts=False,vars=variables,tasks=transform(tasks))]))
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(play)],capture_output=True,text=True,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote')},timeout=30)
                self.assertEqual(result.returncode==0,scenario in ('normal','already-stopped'),result.stdout+result.stderr)
                events=[json.loads(line) for line in (root/'events').read_text().splitlines()]
                stops=[v for v in events if v[:2]==['systemctl','stop']]
                deletes=[v for v in events if v[:3]==['/usr/sbin/nft','delete','table']]
                self.assertEqual(len(stops),0 if scenario in ('already-stopped','unit-mismatch','invocation-mismatch') else 2)
                self.assertEqual(deletes,[['/usr/sbin/nft','delete','table','inet','perkforge_pxe_pilot']] if scenario=='normal' else [])
                self.assertEqual((root/'guard').exists(),scenario not in ('normal','already-stopped'))

    def test_wrapper_dispatches_only_expected_playbooks_with_mock_ansible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'pxe/pilot').mkdir(parents=True)
            (root/'.secrets/pxe-pilot').mkdir(parents=True)
            (root/'.secrets/pxe-pilot/activation-review.yml').write_text('# dummy only\n')
            wrapper=root/'pxe/pilot/pilot.sh'
            wrapper.write_text((ROOT/'pilot.sh').read_text())
            (root/'bin').mkdir()
            fake=root/'bin/ansible-playbook'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$FIXTURE_ARGV"\n')
            fake.chmod(0o700)
            argv=root/'argv'
            env={**os.environ,'PATH':str(root/'bin')+':'+os.environ['PATH'],'FIXTURE_ARGV':str(argv),'BASH_ENV':'/dev/null'}
            for mode in ('activate','retry','rearm','shutdown'):
                run=subprocess.run(['bash',str(wrapper),mode],env=env,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
                args=argv.read_text().splitlines()
                self.assertIn(str(root/f'pxe/pilot/{"activate" if mode=="retry" else mode}.yml'),args)
                self.assertIn('--ask-become-pass',args)
                if mode in ('activate','retry'):
                    self.assertIn('pilot_retry_reviewed_menu='+str(mode=='retry').lower(),args)
                self.assertIn('pilot_activation_approved=true' if mode in ('activate','retry') else ('pilot_rearm_approved=true' if mode=='rearm' else 'pilot_shutdown_approved=true'),args)
                argv.unlink()
            run=subprocess.run(['bash',str(wrapper),'invalid'],env=env,capture_output=True,text=True)
            self.assertEqual(run.returncode,2)
            self.assertFalse(argv.exists())

    def test_port_guard_accepts_only_existing_libvirt_dhcp_binding(self):
        task=next(t for t in yaml.safe_load((ROOT/'activate.yml').read_text())[0]['tasks']
                  if t.get('name','').startswith('Reject occupied'))
        good=['udp UNCONN 0 0 0.0.0.0%virbr0:67 0.0.0.0:*',
              'tcp LISTEN 0 32 127.0.0.1:53 0.0.0.0:*']
        cases=[(good,True),(good+['udp UNCONN 0 0 0.0.0.0:67 0.0.0.0:*'],False),
               (good+['tcp LISTEN 0 32 192.0.2.10:8080 0.0.0.0:*'],False)]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for index,(lines,accepted) in enumerate(cases):
                play=root/f'{index}.yml'
                play.write_text(yaml.safe_dump([dict(hosts='localhost',connection='local',gather_facts=False,
                    vars=dict(initial_sockets=dict(stdout_lines=lines)),tasks=[task])]))
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(play)],capture_output=True,text=True,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local')},timeout=15)
                self.assertEqual(result.returncode==0,accepted,result.stdout+result.stderr)

    def test_numeric_pid_extraction_excludes_new_pilot_and_rejects_invalid_rows(self):
        play=yaml.safe_load((ROOT/'activate.yml').read_text())[0]
        extraction=[t for t in play['tasks'] if t.get('name','').startswith((
            'Require nonempty numeric','Extract original numeric','Validate exact numeric'))]
        block=play['tasks'][-1]['block']
        check=[t for t in block if t.get('name','').startswith((
            'Recheck original dnsmasq','Report PID-query failure','Require unchanged original'))]
        rows=['    110 /usr/sbin/dnsmasq SYNTHETIC_PRIVATE_ARG',
              ' 220 /usr/sbin/dnsmasq --synthetic-config',
              '  221 /usr/sbin/dnsmasq --synthetic-child']
        cases=[('valid',rows,True),('empty',[],False),('blank',[''],False),
               ('text',['oops not a PID'],False),('negative',['-7 bad'],False),
               ('zero',['0 bad'],False),('duplicate',[rows[0],rows[0]],False),
               ('query-error',rows,False),('changed-identity',rows,False)]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for index,(scenario,lines,accepted) in enumerate(cases):
                marker=root/f'argv{index}'
                mock=root/f'ps{index}.py'
                mock.write_text(
                    'import json,sys\nfrom pathlib import Path\n'
                    +f'rows={rows!r}\nmarker=Path({str(marker)!r})\nscenario={scenario!r}\n'
                    +"args=sys.argv[1:]; marker.write_text(json.dumps(args)); pids=args[args.index('-p')+1].split(',')\n"
                    +"if scenario=='query-error':\n print('SYNTHETIC_PRIVATE_ARG',file=sys.stderr); raise SystemExit(1)\n"
                    +"all_rows={r.split()[0]:r for r in rows}; all_rows['99999']='99999 new-pilot'\n"
                    +"for pid in pids:print(all_rows[pid]+(' changed' if scenario=='changed-identity' else ''))\n")
                tasks=json.loads(json.dumps(extraction+check))
                for task in tasks:
                    if 'ansible.builtin.command' in task:
                        argv=task['ansible.builtin.command']['argv']
                        task['ansible.builtin.command']={'argv':[sys.executable,str(mock),*argv]}
                fixture=[dict(hosts='localhost',connection='local',gather_facts=False,
                    vars=dict(dnsmasq_before=dict(stdout='\n'.join(lines),stdout_lines=lines)),tasks=tasks)]
                path=root/f'play{index}.yml';path.write_text(yaml.safe_dump(fixture))
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(path)],capture_output=True,text=True,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote')},timeout=20)
                self.assertEqual(result.returncode==0,accepted,result.stdout+result.stderr)
                self.assertNotIn('SYNTHETIC_PRIVATE_ARG',result.stdout+result.stderr)
                if scenario in ('valid','query-error','changed-identity'):
                    args=json.loads(marker.read_text())
                    self.assertEqual(args[args.index('-p')+1],'110,220,221')
                    self.assertNotIn('99999',str(args))
                else:
                    self.assertFalse(marker.exists(),'Invalid rows must stop before ps')
                if scenario=='query-error':
                    self.assertIn('exit=1',result.stdout)

    def test_retry_menu_guard_accepts_only_its_selected_exact_hash(self):
        tasks=yaml.safe_load((ROOT/'activate.yml').read_text())[0]['tasks']
        chosen=[t for t in tasks if t.get('name','').startswith((
            'Select one exact expected','Require exact stock menu'))]
        original='a'*64
        reviewed='b'*64
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for index,(retry,current,accepted) in enumerate([
                (False,original,True),(False,reviewed,False),
                (True,reviewed,True),(True,original,False),
                (False,'c'*64,False),(True,'c'*64,False)]):
                fixture=[dict(hosts='localhost',connection='local',gather_facts=False,
                    vars=dict(pilot_retry_reviewed_menu=retry,pilot_original_menu_sha256=original,
                        pilot_review_hashes={'grub.cfg':reviewed},
                        old_menu={'stat':{'isreg':True,'islnk':False,'checksum':current}}),tasks=chosen)]
                play=root/f'{index}.yml';play.write_text(yaml.safe_dump(fixture))
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(play)],capture_output=True,text=True,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local')},timeout=15)
                self.assertEqual(result.returncode==0,accepted,result.stdout+result.stderr)
