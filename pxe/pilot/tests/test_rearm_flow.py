"""Rearm task-body positive/expiry flows with real Ansible and fake native commands.

Privilege/served paths are adapted to a temp directory; all command tasks invoke
one mock. This proves task orchestration, not systemd/netlink or outer rescue.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
UNITS = ['perkforge-pxe-pilot-dnsmasq.service', 'perkforge-pxe-pilot-http.service']

class RearmFlow(unittest.TestCase):
    def test_full_task_body_success_expiry_and_guard_mismatch(self):
        for scenario in ('active', 'absent-expired', 'failed-expired', 'guard-changed'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                runtime = root / 'runtime'
                config = runtime / 'config/session-fixture'
                config.mkdir(parents=True)
                archive = config / 'history'
                archive.mkdir()
                hashes = {}
                for name in ['dnsmasq.conf', 'nginx.conf', 'grub.cfg', 'ingress.nft']:
                    data = ('synthetic '+name+'\n').encode()
                    path = config / name
                    path.write_bytes(data)
                    path.chmod(0o600)
                    hashes[name] = hashlib.sha256(data).hexdigest()
                menu = root / 'served-grub.cfg'
                menu.write_bytes((config/'grub.cfg').read_bytes())
                old = ['InvocationID='+char*32+'\nExecStart=test '+str(config) for char in 'ab']
                ledger = config / 'unit-identities.json'
                ledger.write_text(json.dumps(old))
                (archive/'unit-identities-before.json').write_text(json.dumps(old))
                baseline = '110 system-dnsmasq\n220 libvirt-dnsmasq'
                record = dict(config_dir=str(config), hashes=hashes, units=UNITS, dnsmasq_baseline=baseline)
                active = runtime / 'config/active.json'
                active.write_text(json.dumps(record))
                (archive/'active-before.json').write_text(json.dumps(record))
                guard = json.dumps({'nftables':[{'table':{'family':'inet','name':'perkforge_pxe_pilot'}}]})
                state = {unit:('absent' if scenario=='absent-expired' else 'old') for unit in UNITS}
                (root/'states.json').write_text(json.dumps(state))
                (root/'fixture.json').write_text(json.dumps(dict(scenario=scenario, config=str(config), units=UNITS, baseline=baseline, guard=guard)))
                mock = root/'mock.py'
                mock.write_text(r'''import json,sys
from pathlib import Path
root=Path(sys.argv[1]); cmd=sys.argv[2:]; fixture=json.loads((root/'fixture.json').read_text()); states=json.loads((root/'states.json').read_text())
with (root/'events').open('a') as f:f.write(json.dumps(cmd)+'\n')
def save(): (root/'states.json').write_text(json.dumps(states))
if cmd[:2]==['systemctl','stop']:
 states[cmd[2]]='failed' if fixture['scenario']=='failed-expired' else 'absent'; save()
elif cmd[:2]==['systemctl','reset-failed']:
 states[cmd[2]]='absent'; save()
elif cmd[:2]==['systemctl','show']:
 unit=cmd[2]
 if unit=='nginx.service':print('LoadState=masked\nActiveState=inactive')
 elif states[unit]=='absent': print('LoadState=not-found')
 else:
  index=fixture['units'].index(unit); new=states[unit]=='new'; failed=states[unit]=='failed'
  identity=('cd' if new else 'ab')[index]*32
  print('LoadState=loaded\nActiveState='+('failed' if failed else 'active')+'\nMainPID='+('0' if failed else '123')+'\nKillMode=control-group\nInvocationID='+identity+'\nExecStart=/usr/sbin/fixture '+fixture['config']+'\nRuntimeMaxUSec=infinity\nActiveEnterTimestamp=Sat 2026-10-31 00:53:00 UTC')
elif cmd[0]=='systemd-run':
 unit=next(v.split('=',1)[1] for v in cmd if v.startswith('--unit='))
 assert unit in fixture['units'] and states[unit]=='absent'
 assert '--property=RuntimeMaxSec=infinity' in cmd
 states[unit]='new';save()
elif cmd[0]=='/usr/bin/ss':
 if all(v=='new' for v in states.values()):print('udp UNCONN 0 0 192.0.2.10:69 0.0.0.0:*\nudp UNCONN 0 0 192.0.2.10:4011 0.0.0.0:*\ntcp LISTEN 0 32 192.0.2.10:8080 0.0.0.0:*')
elif cmd[0]=='ps':print(fixture['baseline'])
elif cmd[:6]==['/usr/sbin/nft','-j','list','table','inet','perkforge_pxe_pilot']:
 print('CHANGED' if fixture['scenario']=='guard-changed' else fixture['guard'])
else:raise SystemExit('Unmocked command '+repr(cmd))
''')
                def adapt(tasks):
                    out=[]
                    for original in tasks:
                        task=json.loads(json.dumps(original))
                        if 'ansible.builtin.include_tasks' in task:
                            out.extend(adapt(yaml.safe_load((ROOT/task['ansible.builtin.include_tasks']).read_text())))
                            continue
                        if 'ansible.builtin.command' in task:
                            command=task['ansible.builtin.command']
                            argv=command['argv'] if isinstance(command,dict) else command.split()
                            prefix=[sys.executable,str(mock),str(root)]
                            if isinstance(argv,str):
                                assert argv.strip() == '{{ item }}'
                                wrapped='{{ '+json.dumps(prefix)+' + item }}'
                            else:wrapped=[*prefix,*argv]
                            task['ansible.builtin.command']={'argv':wrapped}
                        if 'ansible.builtin.stat' in task and task['ansible.builtin.stat']['path'].startswith('/srv/'):
                            task['ansible.builtin.stat']['path']=str(menu)
                        if 'ansible.builtin.assert' in task:
                            conditions=task['ansible.builtin.assert']['that']
                            if isinstance(conditions,list):
                                task['ansible.builtin.assert']['that']=[v.replace('item.stat.uid == 0',f'item.stat.uid == {os.getuid()}') for v in conditions]
                        for module in ('ansible.builtin.copy','ansible.builtin.file'):
                            if module in task:
                                task[module].pop('owner',None);task[module].pop('group',None)
                        out.append(task)
                    return out
                variables=dict(pilot_record=record,pilot_runtime=str(runtime),pilot_units=UNITS,
                    current_units={'results':[{'item':unit,'stdout':'LoadState=not-found' if scenario=='absent-expired' else 'LoadState=loaded'} for unit in UNITS]},
                    config_session={'path':str(config)},pilot_review_hashes=hashes,pilot_menu_placed=True,
                    original_identities=old,rearm_archive={'path':str(archive)},
                    rearm_guard={'content':base64.b64encode(guard.encode()).decode()},
                    rearm_default={'stdout':'LoadState=masked\nActiveState=inactive'})
                play=root/'play.yml'
                play.write_text(yaml.safe_dump([dict(hosts='localhost',connection='local',gather_facts=False,vars=variables,tasks=adapt(yaml.safe_load((ROOT/'rearm-units.yml').read_text())))]))
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(play)],capture_output=True,text=True,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote')},timeout=40)
                passed=scenario!='guard-changed'
                self.assertEqual(result.returncode==0,passed,result.stdout[-5000:]+result.stderr)
                events=[json.loads(line) for line in (root/'events').read_text().splitlines()]
                launches=[v for v in events if v[0]=='systemd-run']
                self.assertEqual(len(launches),2 if passed else 0)
                if passed:
                    new=json.loads(ledger.read_text())
                    self.assertNotEqual(new,old)
                    self.assertEqual(len(new),2)
                    self.assertEqual(json.loads(active.read_text())['lifetime_seconds'],'infinity')
                else:self.assertEqual(json.loads(ledger.read_text()),old)
                resets=[v for v in events if v[:2]==['systemctl','reset-failed']]
                self.assertEqual(len(resets),2 if scenario=='failed-expired' else 0)
                self.assertEqual(json.loads((archive/'unit-identities-before.json').read_text()),old)
                self.assertFalse(any(v[0]=='/usr/sbin/nft' and ('delete' in v or '-f' in v) for v in events))
