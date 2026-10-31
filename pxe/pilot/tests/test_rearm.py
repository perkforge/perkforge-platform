"""Offline rearm checks: source ordering and real Ansible assertions, no sockets."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]

class RearmTests(unittest.TestCase):
    def test_rearm_has_explicit_gate_and_never_modifies_guard_or_media(self):
        play=yaml.safe_load((ROOT/'rearm.yml').read_text())[0]
        tasks=yaml.safe_load((ROOT/'rearm-units.yml').read_text())
        self.assertFalse(play['vars']['pilot_rearm_approved'])
        self.assertIn('pilot_rearm_approved | bool',play['tasks'][0]['ansible.builtin.assert']['that'])
        alltext=(ROOT/'rearm.yml').read_text()+(ROOT/'rearm-units.yml').read_text()
        for forbidden in ('/srv/', 'ansible.builtin.template', 'nft, -f', 'nft delete', 'set-property'):
            self.assertNotIn(forbidden,alltext)
        stop=next(i for i,t in enumerate(tasks) if t.get('name','').startswith('Stop only'))
        archive_withdraw=next(i for i,t in enumerate(tasks) if t.get('name','').startswith('Withdraw old live'))
        start=next(i for i,t in enumerate(tasks) if t.get('name','').startswith('Recreate only'))
        self.assertLess(stop,archive_withdraw)
        self.assertLess(archive_withdraw,start)
        launch=tasks[start]['loop']
        self.assertEqual(len(launch),2)
        self.assertTrue(all('--property=RuntimeMaxSec=infinity' in argv for argv in launch))
        text=(ROOT/'rearm.yml').read_text()
        self.assertLess(text.index('Preserve original identity ledger'),text.index('rearm-units.yml'))
        self.assertIn('identity_file.stat.exists',text)
        self.assertIn('guard retained',text)

    def test_new_runtime_and_identity_assertions_require_approved_unbounded_choice(self):
        tasks=yaml.safe_load((ROOT/'rearm-units.yml').read_text())
        index=next(i for i,t in enumerate(tasks) if t.get('name','').startswith('Capture and validate'))
        assertion=tasks[index+1]
        config='/run/perkforge-pxe-pilot/config/session-test'
        old=['InvocationID='+'a'*32,'InvocationID='+'b'*32]
        def rows(runtime='infinity',pid='123',same=False):
            return [{'item':name,'stdout_lines':['ActiveState=active','RuntimeMaxUSec='+runtime],
                     'stdout':'ActiveState=active\nRuntimeMaxUSec='+runtime+'\nMainPID='+pid+
                     '\nActiveEnterTimestamp=Sat 2026-10-31 00:50:00 UTC\nInvocationID='+
                     (('a' if i==0 else 'b') if same else ('c' if i==0 else 'd'))*32+
                     '\nExecStart=/usr/sbin/test '+config}
                    for i,name in enumerate(['perkforge-pxe-pilot-dnsmasq.service','perkforge-pxe-pilot-http.service'])]
        cases=[(rows(),True),(rows(runtime='30min'),False),(rows(runtime='2h'),False),
               (rows(pid='0'),False),(rows(same=True),False)]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,(result,accepted) in enumerate(cases):
                play=root/f'{i}.yml'
                play.write_text(yaml.safe_dump([dict(hosts='localhost',connection='local',gather_facts=False,
                    vars=dict(config_session={'path':config},original_identities=old,rearmed_units={'results':result}),
                    tasks=[assertion])]))
                proc=subprocess.run(['ansible-playbook','-i','localhost,',str(play)],capture_output=True,text=True,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local')},timeout=15)
                self.assertEqual(proc.returncode==0,accepted,proc.stdout+proc.stderr)

    def test_expired_absent_units_still_require_protected_prior_identity_records(self):
        play=yaml.safe_load((ROOT/'rearm.yml').read_text())[0]
        require=next(t for t in play['tasks'] if t.get('name','').startswith('Require trusted prior'))
        identity_tasks=yaml.safe_load((ROOT/'verify-pilot-identity.yml').read_text())
        allow_absent=next(t for t in identity_tasks if 'ansible.builtin.assert' in t
                          and any('LoadState=not-found' in str(v) for v in t['ansible.builtin.assert']['that']))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,(has_record,accepted) in enumerate([(True,True),(False,False)]):
                variables=dict(identity_file={'stat':{'exists':has_record}},
                    recorded_identities=['InvocationID='+'a'*32,'InvocationID='+'b'*32],
                    pilot_units=['perkforge-pxe-pilot-dnsmasq.service','perkforge-pxe-pilot-http.service'],
                    pilot_record={'config_dir':'/run/perkforge-pxe-pilot/config/session-test',
                                  'hashes':{n:'0'*64 for n in ['dnsmasq.conf','nginx.conf','grub.cfg','ingress.nft']}},
                    current_units={'results':[{'stdout':'LoadState=not-found','item':'perkforge-pxe-pilot-dnsmasq.service'}]})
                path=root/f'{i}.yml'
                path.write_text(yaml.safe_dump([dict(hosts='localhost',connection='local',gather_facts=False,
                    vars=variables,tasks=[allow_absent,require])]))
                proc=subprocess.run(['ansible-playbook','-i','localhost,',str(path)],capture_output=True,text=True,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local')},timeout=15)
                self.assertEqual(proc.returncode==0,accepted,proc.stdout+proc.stderr)
