"""Offline only. Socket constructors are mocked; cleanup commands are temp mocks."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('packet_probe', ROOT / 'probe_packets.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

class PacketFixtureTests(unittest.TestCase):
    def test_packet_encoding_and_4011_boot_item(self):
        with patch.object(probe.socket, 'socket', side_effect=AssertionError('No offline sockets')):
            for port in (67, 4011):
                raw = probe.frame(probe.request(0x12345678, port=port), probe.MAC, port)
                parsed = probe.decode(raw)
                self.assertEqual(parsed['xid'], 0x12345678)
                self.assertEqual(parsed['dport'], port)
                self.assertEqual(parsed['opts'][93], b'\0\x07')
                self.assertEqual(parsed['opts'][53], bytes([1 if port == 67 else 3]))
                self.assertEqual(probe.checksum(raw[14:34]), 0)
                if port == 4011:
                    self.assertEqual(probe.options(parsed['opts'][43])[71], b'\x80\0\0\0')
            with self.assertRaises(ValueError):
                probe.options(b'\x35\x02\x01')

    def test_namespace_guard_prevents_host_socket_creation(self):
        with patch.object(probe.subprocess, 'check_output', return_value=''), \
             patch.object(probe.socket, 'socket') as sock:
            with self.assertRaises(RuntimeError):
                probe.Probes().suite('daemon')
            sock.assert_not_called()

    def test_negative_evidence_requires_server_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event = dict(xid=123, dport=4011, mac=probe.UNKNOWN.hex())
            observation = root/'observation'
            observation.write_text(json.dumps({'ready': True})+'\n')
            results = []
            for phase in ('daemon', 'guarded'):
                path = root/phase
                path.write_text(json.dumps(dict(result='PASS', requests=[event])))
                results.append(str(path))
            with self.assertRaises(AssertionError):
                probe.verify_observations([str(observation), *results])
            observation.write_text(json.dumps(event)+'\n')
            with contextlib.redirect_stdout(io.StringIO()):
                probe.verify_observations([str(observation), *results])

    def test_fixture_has_explicit_gate_and_no_host_network_commands(self):
        play = yaml.safe_load((ROOT/'packet-fixture.yml').read_text())[0]
        self.assertFalse(play['vars']['fixture_execution_approved'])
        self.assertIn('fixture_execution_approved | bool', play['tasks'][0]['ansible.builtin.assert']['that'])
        tasks = play['tasks'][-1]['block']
        templates = next(t for t in tasks if 'ansible.builtin.template' in t)
        self.assertEqual(templates['ansible.builtin.template']['src'], 'templates/{{ item }}.j2')
        for task in tasks:
            command = task.get('ansible.builtin.command', {})
            argv = command.get('argv', []) if isinstance(command, dict) else []
            if '/usr/sbin/nft' in argv:
                self.assertEqual(argv[:4], ['/usr/bin/ip','netns','exec','pfpxe-s'])
        self.assertIn('always', play['tasks'][-1])
        self.assertNotIn('ansible.builtin.apt', (ROOT/'packet-fixture.yml').read_text())

    def test_cleanup_mocks_normal_and_identity_or_residual_failures(self):
        # Execute actual cleanup tasks, replacing only command paths/stat roots.
        # Mock operations can mutate only this TemporaryDirectory; no real ip,
        # systemctl, sudo, namespace, listener or firewall invocation occurs.
        for scenario in ('normal', 'unit-mismatch', 'invocation-mismatch', 'inode-mismatch', 'residual-pid', 'partial-namespace'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                events=root/'events'
                state=root/'state'
                state.write_text(json.dumps(['pfpxe-s','pfpxe-c']))
                for name in ('pfpxe-s','pfpxe-c'):
                    (root/name).touch()
                owned={name:(root/name).stat().st_ino for name in ('pfpxe-s','pfpxe-c')}
                if scenario=='inode-mismatch':
                    owned['pfpxe-s']+=1
                if scenario=='partial-namespace':
                    owned={}
                mock=root/'mock.py'
                mock.write_text('''import json,sys
from pathlib import Path
root=Path(sys.argv[1]); scenario=sys.argv[2]; cmd=sys.argv[3:]
with (root/'events').open('a') as f: f.write(json.dumps(cmd)+'\\n')
if cmd[:2]==['systemctl','show']:
 print('LoadState=loaded'); print('ActiveState=inactive'); print('InvocationID='+'1'*32)
 print('ExecStart=/usr/bin/ip netns exec pfpxe-s '+str(root if scenario!='unit-mismatch' else root/'OTHER')+'/config/run')
 if scenario=='unit-mismatch': print('MISMATCH')
elif cmd[:2]==['systemctl','stop']: pass
elif cmd[:3]==['/usr/bin/ip','netns','pids']:
 if scenario=='residual-pid': print('99999')
elif cmd[:3]==['/usr/bin/ip','netns','delete']:
 names=json.loads((root/'state').read_text()); names.remove(cmd[3]); (root/'state').write_text(json.dumps(names))
elif cmd[:3]==['/usr/bin/ip','netns','list']:
 print('\\n'.join(json.loads((root/'state').read_text())))
else: raise SystemExit('Unexpected mock operation '+repr(cmd))
''')
                tasks=yaml.safe_load((ROOT/'packet-cleanup.yml').read_text())
                for task in tasks:
                    if 'ansible.builtin.command' in task:
                        command=task['ansible.builtin.command']
                        argv=command['argv'] if isinstance(command,dict) else command.split()
                        task['ansible.builtin.command']={'argv':[sys.executable,str(mock),str(root),scenario,*argv]}
                    if 'ansible.builtin.stat' in task:
                        task['ansible.builtin.stat']['path']=str(root)+'/{{ item.key }}'
                # Wrong ExecStart must lack run's unique path entirely.
                if scenario=='unit-mismatch':
                    mock.write_text(mock.read_text().replace("root/'OTHER'", "Path('/different-run')"))
                fixture=[dict(hosts='localhost',connection='local',gather_facts=False,
                    vars=dict(fixture_units=['pfpxe-fixture-observer.service'],fixture_namespaces=['pfpxe-s','pfpxe-c'],
                              fixture_dir=dict(path=str(root)),namespace_owned=owned),tasks=tasks)]
                if scenario=='invocation-mismatch':
                    fixture[0]['vars']['fixture_invocations']={'results':[{'stdout':'0'*32}]}
                play=root/'cleanup.yml';play.write_text(yaml.safe_dump(fixture))
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(play)],capture_output=True,text=True,
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'ansible-local'),'ANSIBLE_REMOTE_TEMP':str(root/'ansible-remote')},timeout=30)
                self.assertEqual(result.returncode==0,scenario=='normal',result.stdout+result.stderr)
                commands=[json.loads(line) for line in events.read_text().splitlines()]
                deletes=[c for c in commands if c[:3]==['/usr/bin/ip','netns','delete']]
                self.assertEqual(len(deletes),2 if scenario=='normal' else 0)
                if scenario in ('unit-mismatch','invocation-mismatch'):
                    self.assertFalse(any(c[:2]==['systemctl','stop'] for c in commands))
