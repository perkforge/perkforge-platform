"""Offline real-task sequencing with all reboot/host/API operations mocked."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parent
NODES=['worker-a','worker-b','control-a']
UID='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
MOCK=r'''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
p=Path(os.environ['REBOOT_STATE']);s=json.loads(p.read_text())
a=sys.argv[1:];role=a.pop(0)
if role=='node':
 node=a.pop(0);s['calls'].append([node,*a]);out=''
 if a==['hostname']:out=node
 elif a[0]=='reboot':
  s['sequence'].append(node)
  if s['scenario']=='reboot-fails':p.write_text(json.dumps(s));sys.exit(1)
  s['boots'][node]='after-'+node
 elif a[0]=='cat':out=s['boots'][node]
 elif a[0]=='getenforce':out='Enforcing'
 elif a[0]=='sysctl':out='1\n1\n1'
 elif a[:2]==['systemctl','is-enabled']:out='disabled' if a[2]=='firewalld' else 'enabled'
 elif a[:2]==['systemctl','is-active']:out='active'
 else:raise SystemExit('Unexpected mocked host command: '+repr(a))
 print(out)
else:
 a=a[3:]
 s['calls'].append(['kubectl',*a])
 def node(name):
  boot=s['boots'][name]
  if s['scenario']=='stale-api':boot='before-'+name
  return {'metadata':{'name':name},'status':{'nodeInfo':{'bootID':boot},'conditions':[{'type':'Ready','status':'True'}]}}
 if a[:2]==['get','namespace']:print(json.dumps({'metadata':{'uid':os.environ['REBOOT_UID']}}))
 elif a[:2]==['get','nodes']:print(json.dumps({'items':[node(n) for n in s['boots']]}))
 elif a[:2]==['get','node']:print(json.dumps(node(a[2])))
 elif a[:2]==['get','pods']:print(json.dumps({'items':[{'metadata':{'namespace':'kube-system','name':'fixture'},'status':{'phase':'Running'}}]}))
 elif a[:2]==['get','--raw=/readyz']:print('ok')
 elif a[0]=='wait':print('Ready')
 else:raise SystemExit('Unexpected mocked API command: '+repr(a))
p.write_text(json.dumps(s))
'''

class RebootVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        self.mock=self.work/'mock';self.mock.write_text(MOCK);self.mock.chmod(0o700)
        self.client=self.work/'kubectl'
        self.client.write_text('#!/bin/sh\nexec "'+str(self.mock)+'" api "$@"\n');self.client.chmod(0o700)
        self.config=self.work/'config';self.config.write_text('SYNTHETIC_PRIVATE_KUBECONFIG');self.config.chmod(0o600)
        self.output=self.work/'results';self.output.mkdir(mode=0o700)
        self.backup=self.work/'backup';self.backup.mkdir(mode=0o700)
        body=b'SYNTHETIC_NOT_REAL_ETCD'.ljust(512,b'\0');snapshot=body+hashlib.sha256(body).digest()
        (self.backup/'snapshot.db').write_bytes(snapshot)
        (self.backup/'server-token.secure').write_text('SYNTHETIC_RECOVERY_SECRET')
        (self.backup/'summary.yml').write_text(yaml.safe_dump(dict(backup_verified=True,cluster_uid=UID,cluster_id='fixture',snapshot_sha256=hashlib.sha256(snapshot).hexdigest())))
        for p in self.backup.iterdir():p.chmod(0o600)
        for node in NODES:
            folder=self.work/node;folder.mkdir()
            (folder/'owner.json').write_text(json.dumps(dict(owner='perkforge-infrastructure',cluster='fixture',role='server' if node=='control-a' else 'agent')))
        for module in ['overlay','br_netfilter','nf_conntrack']:(self.work/'modules'/module).mkdir(parents=True)
        self.inventory=self.work/'inventory.yml'
        hosts={n:{'ansible_host':'192.0.2.1','ansible_user':'fixture','ansible_connection':'local'} for n in NODES}
        self.inventory.write_text(yaml.safe_dump({'all':{'children':{'rke2_servers':{'hosts':{'control-a':hosts['control-a']}},'rke2_agents':{'hosts':{n:hosts[n] for n in NODES[:2]}}}}},sort_keys=False))
        self.state=self.work/'state.json'
        main=yaml.safe_load((ROOT/'reboot-verification.yml').read_text())
        main[0]['vars_files']=[str(ROOT.parent/'group_vars/rke2.yml')]
        def transform(v):
            if isinstance(v,list):return [transform(x) for x in v]
            if isinstance(v,dict):
                d={k:(1 if k=='retries' else 0 if k=='delay' else transform(x)) for k,x in v.items() if k not in ['delegate_to','become']}
                if 'ansible_connection' in d:d['ansible_connection']='local'
                if 'ansible.builtin.reboot' in d:
                    del d['ansible.builtin.reboot']
                    d['ansible.builtin.command']={'argv':[str(self.mock),'node','{{ reboot_target }}','reboot']}
                elif 'ansible.builtin.command' in d:
                    a=d['ansible.builtin.command'].get('argv')
                    if isinstance(a,list) and a and a[0] in ['hostname','systemctl','cat','getenforce','sysctl']:
                        d['ansible.builtin.command']['argv']=[str(self.mock),'node','{{ reboot_target }}',*a]
                return d
            if isinstance(v,str):
                return v.replace('reboot-node.yml',str(self.work/'node.yml')).replace('{{ playbook_dir }}/verify_etcd_snapshot.py',str(ROOT/'verify_etcd_snapshot.py')).replace('/etc/rancher/rke2/perkforge-owner.json',str(self.work)+'/{{ reboot_target }}/owner.json').replace('/sys/module/',str(self.work/'modules')+'/')
            return v
        node=transform(yaml.safe_load((ROOT/'reboot-node.yml').read_text()))
        self.assertNotIn('ansible.builtin.reboot',str(node))
        (self.work/'node.yml').write_text(yaml.safe_dump(node))
        self.play=self.work/'play.yml';self.play.write_text(yaml.safe_dump(transform(main)))
        self.values=dict(reboot_verification_apply=True,rke2_cluster_id='fixture',reboot_kubeconfig=str(self.config),reboot_kubectl=str(self.client),reboot_expected_cluster_uid=UID,reboot_output_parent=str(self.output),reboot_backup_directory=str(self.backup))

    def invoke(self,scenario='success',check=False,**overrides):
        self.state.write_text(json.dumps(dict(boots={n:'before-'+n for n in NODES},sequence=[],calls=[],scenario=scenario)))
        p=subprocess.run(['ansible-playbook','-i',str(self.inventory),str(self.play),'-e',json.dumps({**self.values,**overrides}),*(['--check'] if check else [])],text=True,capture_output=True,timeout=150,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.work/'ansible'),'ANSIBLE_REMOTE_TEMP':str(self.work/'remote'),'REBOOT_STATE':str(self.state),'REBOOT_UID':UID})
        for secret in ['SYNTHETIC_PRIVATE_KUBECONFIG','SYNTHETIC_RECOVERY_SECRET']:self.assertNotIn(secret,p.stdout+p.stderr)
        return p,json.loads(self.state.read_text())

    def test_defaults_check_and_wrong_cluster_never_reboot(self):
        for values in [dict(reboot_verification_apply=False),dict(check=True)]:
            p,s=self.invoke(**values)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertEqual(s['calls'],[])
        p,s=self.invoke(reboot_expected_cluster_uid='ffffffff-bbbb-cccc-dddd-eeeeeeeeeeee')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(s['sequence'],[])

    def test_worker_first_sequence_requires_new_boot_ids(self):
        p,s=self.invoke()
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertEqual(s['sequence'],NODES)
        summary=next(self.output.glob('*/summary.yml'))
        evidence=yaml.safe_load(summary.read_text())
        self.assertTrue(evidence['reboots_passed'])
        self.assertEqual(evidence['completed'],NODES)
        self.assertEqual(summary.stat().st_mode & 0o777,0o600)
        for n in NODES:
            d=yaml.safe_load((summary.parent/(n+'.yml')).read_text())
            self.assertNotEqual(d['boot_id_before'],d['boot_id_after'])

    def test_failure_or_stale_api_stops_before_second_worker(self):
        for scenario in ['reboot-fails','stale-api']:
            with self.subTest(scenario=scenario):
                p,s=self.invoke(scenario)
                self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                self.assertEqual(s['sequence'],NODES[:1])
                summary=max(self.output.glob('*/summary.yml'),key=lambda p:p.stat().st_mtime_ns)
                d=yaml.safe_load(summary.read_text())
                self.assertFalse(d['reboots_passed'])
                self.assertEqual(d['completed'],[])
                self.assertEqual(d['in_progress_or_failed_node'],'worker-a')

if __name__=='__main__':unittest.main()
