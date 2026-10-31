"""Real Ansible offline preparation: synthetic metadata, new temp files only."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]

class Preparation(unittest.TestCase):
    def run_plan(self, root, extra=None, check=False):
        values={'output_dir':str(root/'plan')}
        values.update(extra or {})
        inputs=root/'inputs.yml';inputs.write_text(yaml.safe_dump(values))
        args=['ansible-playbook','-i','localhost,','-c','local',str(ROOT/'ansible/prepare.yml'),'-e','@'+str(inputs)]
        if check:args.append('--check')
        return subprocess.run(args,capture_output=True,text=True,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote')},timeout=25)

    def test_default_unknown_metadata_renders_only_blocked_artifacts(self):
        with tempfile.TemporaryDirectory(prefix='perkforge-pxe-plan-fixture-') as folder:
            root=Path(folder);out=Path(folder+'-output')
            try:
                result=self.run_plan(root,{'output_dir':str(out)})
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(set(p.name for p in out.iterdir()),{'plan.md','install.ks.BLOCKED'})
                self.assertEqual(out.stat().st_mode&0o777,0o700)
                for path in out.iterdir():self.assertEqual(path.stat().st_mode&0o777,0o600)
                self.assertIn('UNCONFIGURED',(out/'plan.md').read_text())
                self.assertIn('exit 1',(out/'install.ks.BLOCKED').read_text())
                result=self.run_plan(root,{'output_dir':str(out)})
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(set(p.name for p in out.iterdir()),{'plan.md','install.ks.BLOCKED'})
            finally:
                if out.exists():
                    for path in out.iterdir():path.unlink()
                    out.rmdir()

    def test_filled_synthetic_plan_stays_blocked_and_check_mode_writes_nothing(self):
        with tempfile.TemporaryDirectory(prefix='perkforge-pxe-plan-fixture-') as folder:
            root=Path(folder);out=Path(folder+'-output')
            values=dict(output_dir=str(out),hostname='fixture.invalid',boot_nic_mac='02:00:00:00:00:11',
                boot_method='PXE_TFTP',installation_source_url='http://192.0.2.10/rhel10/',timezone='Etc/UTC',
                ntp_server='time.example.invalid',bootstrap_username='fixture',
                bootstrap_public_key='ssh-ed25519 AAAA dummy-only',disk_stable_id='disk/by-id/fixture',disk_serial='DUMMY',disk_capacity_bytes=100000000000)
            result=self.run_plan(root,values,True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertFalse(out.exists())
            try:
                result=self.run_plan(root,values)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('BLOCKED',(out/'plan.md').read_text())
                self.assertIn('fixture.invalid',(out/'plan.md').read_text())
                self.assertIn('url --url="http://192.0.2.10/rhel10/"',(out/'install.ks.BLOCKED').read_text())
                self.assertIn('exit 1',(out/'install.ks.BLOCKED').read_text())
            finally:
                if out.exists():
                    for path in out.iterdir():path.unlink()
                    out.rmdir()

    def test_unsafe_or_secret_inputs_fail_before_any_output(self):
        cases=[{'output_dir':'/etc/dnsmasq.d/unsafe'},
               {'installation_source_url':'http://user:password@192.0.2.10/source'},
               {'installation_source_url':'http://192.0.2.10/source?token=bad'},
               {'hostname':'host\nrootpw injected'},
               {'bootstrap_public_key':'-----BEGIN OPENSSH PRIVATE KEY-----'},
               {'credential_mode':'passwordless-sudo'}]
        with tempfile.TemporaryDirectory(prefix='perkforge-pxe-plan-fixture-') as folder:
            root=Path(folder);out=Path(folder+'-output')
            for case in cases:
                with self.subTest(fields=list(case)):
                    result=self.run_plan(root,{'output_dir':str(out),**case})
                    self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertFalse(out.exists())
                    self.assertNotIn('user:password',result.stdout+result.stderr)

    def test_playbook_has_no_native_apply_or_network_operations(self):
        text=(ROOT/'ansible/prepare.yml').read_text()
        for forbidden in ['ansible.builtin.command:','ansible.builtin.shell:','ansible.builtin.service:',
                          'ansible.builtin.systemd','ansible.builtin.package:','handlers:','become: true']:
            self.assertNotIn(forbidden,text)
        self.assertIn('gather_facts: false',text)
        self.assertIn('hosts: localhost',text)
