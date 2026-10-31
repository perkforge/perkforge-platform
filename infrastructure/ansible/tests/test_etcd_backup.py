"""Offline snapshot byte-integrity and real-playbook guards/exports with mocks."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('snapshot_verify',ROOT/'verify_etcd_snapshot.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)

class SnapshotIntegrityTests(unittest.TestCase):
    def test_valid_corrupt_missing_and_truncated_integrity_trailer(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'snapshot.db'
            body=b'SYNTHETIC_NOT_AN_ETCD_DATABASE'.ljust(1024,b'\0')
            valid=body+hashlib.sha256(body).digest()
            p.write_bytes(valid)
            self.assertEqual(verifier.verify(p)['sha256'],hashlib.sha256(valid).hexdigest())
            for bad in [body,valid[:-1],b'x'+valid[1:],valid[:-32]+bytes(32)]:
                p.write_bytes(bad)
                with self.assertRaises(ValueError):verifier.verify(p)
            link=Path(temp)/'link';link.symlink_to(p)
            with self.assertRaises(OSError):verifier.verify(link)

class EtcdBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        self.uid='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        self.token='K10'+'a'*64+'::server:SYNTHETIC_RECOVERY_NEVER_LOG'
        self.tokenfile=self.work/'server-token';self.tokenfile.write_text(self.token+'\n')
        self.owner=self.work/'owner.json'
        self.owner.write_text(json.dumps(dict(owner='perkforge-infrastructure',cluster='fixture-cluster',role='server')))
        self.state=self.work/'private';self.state.mkdir(mode=0o700)
        (self.state/'perkforge-cluster-id').write_text('fixture-cluster')
        self.snapshots=self.work/'snapshots';self.snapshots.mkdir()
        self.kubeconfig=self.work/'kubeconfig';self.kubeconfig.write_text('SYNTHETIC_KUBECONFIG_SECRET');self.kubeconfig.chmod(0o600)
        self.calls=self.work/'calls'
        self.client=self.work/'kubectl'
        self.client.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
with open(os.environ['BACKUP_CALLS'],'a') as f:f.write('kubectl '+repr(sys.argv[1:])+'\\n')
print(json.dumps({'metadata':{'uid':os.environ['BACKUP_UID']}}) if 'namespace' in sys.argv else 'ok')
''');self.client.chmod(0o700)
        self.rke2=self.work/'rke2'
        self.rke2.write_text('''#!/usr/bin/python3
import hashlib,os,sys
from pathlib import Path
with open(os.environ['BACKUP_CALLS'],'a') as f:f.write('rke2 '+repr(sys.argv[1:])+'\\n')
a=sys.argv[1:]
if a==['--version']:print('rke2 version v1.36.5+rke2r1 (synthetic)')
else:
 assert a[:2]==['etcd-snapshot','save']
 assert '--etcd-s3=false' in a
 body=b'SYNTHETIC_SNAPSHOT_NOT_REAL_ETCD'.ljust(1024,b'\\0')
 (Path(a[a.index('--dir')+1])/(a[a.index('--name')+1]+'-fixture-123')).write_bytes(body+hashlib.sha256(body).digest())
 if os.environ['BACKUP_SCENARIO']=='token-changed':Path(os.environ['BACKUP_TOKEN']).write_text('changed-after-snapshot')
''');self.rke2.chmod(0o700)
        self.inventory=self.work/'inventory.yml'
        self.inventory.write_text(yaml.safe_dump({'all':{'vars':{'ansible_connection':'local'},'children':{'rke2_servers':{'hosts':{'fixture-server':{}}},'rke2_agents':{'hosts':{}}}}}))
        plays=yaml.safe_load((ROOT/'etcd-backup.yml').read_text())
        def transform(v):
            if isinstance(v,dict):return {k:transform(x) for k,x in v.items()}
            if isinstance(v,list):return [transform(x) for x in v]
            if isinstance(v,str):
                return v.replace('/usr/bin/rke2',str(self.rke2)).replace('/etc/rancher/rke2/perkforge-owner.json',str(self.owner)).replace('/var/lib/rancher/rke2/server/token',str(self.tokenfile)).replace('{{ playbook_dir }}/verify_etcd_snapshot.py',str(ROOT/'verify_etcd_snapshot.py'))
            return v
        plays=transform(plays)
        for play in plays:
            if 'vars_files' in play:play['vars_files']=[str(ROOT.parent/'group_vars/rke2.yml')]
        plays[1]['become']=False
        plays[1]['vars']['backup_snapshot_directory']=str(self.snapshots)
        self.play=self.work/'play.yml';self.play.write_text(yaml.safe_dump(plays))
        self.values=dict(etcd_backup_apply=True,rke2_cluster_id='fixture-cluster',rke2_private_output_dir=str(self.state),etcd_backup_kubeconfig=str(self.kubeconfig),etcd_backup_kubectl=str(self.client),etcd_backup_output_parent=str(self.state),etcd_backup_expected_cluster_uid=self.uid)

    def invoke(self,scenario='success',check=False,**overrides):
        p=subprocess.run(['ansible-playbook','-i',str(self.inventory),str(self.play),'-e',json.dumps({**self.values,**overrides}),*(['--check'] if check else [])],capture_output=True,text=True,timeout=90,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.work/'ansible'),'ANSIBLE_REMOTE_TEMP':str(self.work/'remote'),'BACKUP_CALLS':str(self.calls),'BACKUP_UID':self.uid,'BACKUP_TOKEN':str(self.tokenfile),'BACKUP_SCENARIO':scenario})
        for secret in [self.token,'SYNTHETIC_KUBECONFIG_SECRET']:self.assertNotIn(secret,p.stdout+p.stderr)
        return p

    def test_defaults_check_and_wrong_cluster_never_snapshot(self):
        for values in [dict(etcd_backup_apply=False),dict(check=True)]:
            p=self.invoke(**values)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertFalse(self.calls.exists())
        p=self.invoke(etcd_backup_expected_cluster_uid='ffffffff-bbbb-cccc-dddd-eeeeeeeeeeee')
        self.assertNotEqual(p.returncode,0)
        self.assertNotIn('rke2',self.calls.read_text())
        self.assertFalse(list(self.snapshots.iterdir()))

    def test_success_exports_matching_protected_bundle(self):
        p=self.invoke()
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        bundle=next(self.state.glob('etcd-backup-*'))
        summary=yaml.safe_load((bundle/'summary.yml').read_text())
        self.assertTrue(summary['backup_verified'])
        self.assertFalse(summary['restore_tested'])
        self.assertTrue(summary['cluster_ready'])
        self.assertEqual((bundle/'server-token.secure').read_text(),self.token+'\n')
        self.assertEqual(summary['snapshot_sha256'],verifier.verify(bundle/'snapshot.db')['sha256'])
        self.assertEqual(bundle.stat().st_mode & 0o777,0o700)
        for name in ['snapshot.db','server-token.secure','summary.yml']:
            self.assertEqual((bundle/name).stat().st_mode & 0o777,0o600)

    def test_changed_token_refuses_a_successful_bundle(self):
        p=self.invoke(scenario='token-changed')
        self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
        bundle=next(self.state.glob('etcd-backup-*'))
        self.assertFalse(yaml.safe_load((bundle/'summary.yml').read_text())['backup_verified'])
        self.assertFalse((bundle/'server-token.secure').exists())
        self.assertEqual(len(list(self.snapshots.iterdir())),1)

if __name__=='__main__':unittest.main()
