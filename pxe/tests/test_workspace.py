"""Real offline workspace rebuilds in disposable checkouts; no native services."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid
import yaml

ROOT = Path(__file__).resolve().parents[1] / 'transport'

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pxe-workspace-test-')
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.repo = self.work / 'checkout'
        self.pilot = self.repo / 'pxe/transport'
        self.pilot.mkdir(parents=True)
        for name in ['workspace.yml', 'workspace.inputs.example.yml', 'prepare.yml',
                     'inputs.example.yml', 'preserve-session.yml']:
            shutil.copy2(ROOT / name, self.pilot / name)
        shutil.copytree(ROOT / 'templates', self.pilot / 'templates')
        self.run = uuid.uuid4().hex[:16]
        self.values = dict(workspace_node='fixture', workspace_run=self.run,
            workspace_menu_state='reviewed', workspace_lifetime_seconds=0,
            workspace_metadata_source='synthetic inventory fixture',
            pxe_interface='fixture0', pxe_server_ip='192.0.2.10',
            pxe_pilot_ip='192.0.2.11', pxe_pilot_mac='02:00:00:00:00:11',
            pxe_network='192.0.2.0', pxe_netmask='255.255.255.0',
            pxe_service_user='nobody', pxe_service_group='nogroup',
            pxe_http_user='www-data', pxe_http_group='www-data',
            pxe_tftp_ownership_policy='root-readonly', pxe_media_layout_reviewed=True,
            pxe_boot_candidates_reviewed=True, pxe_csa=7,
            pxe_efi_entry='fixture/ENTRY.EFI', pxe_grub_config_relative='fixture/grub.cfg',
            pxe_kernel_relative='fixture/vmlinuz', pxe_initrd_relative='fixture/initrd.img',
            pxe_linux_command='linuxefi', pxe_initrd_command='initrdefi')
        self.env = {**os.environ, 'ANSIBLE_LOCAL_TEMP': str(self.work / 'local-tmp'),
                    'ANSIBLE_REMOTE_TEMP': str(self.work / 'remote-tmp'), 'ANSIBLE_NOCOLOR': '1'}
        self.reviews = []
        self.addCleanup(self.clean_reviews)

    def clean_reviews(self):
        for path in self.reviews:
            if path.exists(): shutil.rmtree(path)

    def build(self, values):
        review = Path('/tmp') / ('perkforge-pxe-review-' + values['workspace_node'] + '-' + values['workspace_run'])
        if review not in self.reviews:
            self.assertFalse(review.exists(), 'Never operate on an unknown existing fixture path')
            self.reviews.append(review)
        source = self.work / 'input.yml'
        source.write_text(yaml.safe_dump(values))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local',
            str(self.pilot / 'workspace.yml'), '-e', '@' + str(source)],
            capture_output=True, text=True, env=self.env, timeout=40)
        output = self.repo / 'pxe/local' / values['workspace_node'] / 'runs' / values['workspace_run']
        return result, output, review

    def test_rebuild_from_retained_inputs_and_refuse_overwrite(self):
        result, output, review = self.build({**self.values, 'unexpected_secret': 'SYNTHETIC_DO_NOT_COPY'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = yaml.safe_load((output / 'discovery/activation-review.yml').read_text())
        self.assertTrue(manifest['pilot_retry_reviewed_menu'])
        self.assertEqual(manifest['pilot_lifetime_seconds'], 0)
        self.assertNotIn('pilot_activation_approved', manifest)
        for name, digest in manifest['pilot_review_hashes'].items():
            self.assertEqual((output / 'discovery' / name).read_bytes(), (review / name).read_bytes())
            self.assertEqual(hashlib.sha256((review / name).read_bytes()).hexdigest(), digest)
        for path in output.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o777,
                             0o700 if path.is_dir() or path.name == 'session.sh' else 0o600)
            if path.is_file(): self.assertNotIn('SYNTHETIC_DO_NOT_COPY', path.read_text())
        self.assertEqual(list((output / 'access').iterdir()), [])
        self.assertEqual(subprocess.run(['bash', '-n', str(output / 'session.sh')]).returncode, 0)
        before = (output / 'discovery/activation-review.yml').read_bytes()
        evidence = output / 'discovery/retained-evidence.txt'
        evidence.write_text('preserve me')
        repeated, _, _ = self.build(self.values)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(evidence.read_text(), 'preserve me')
        self.assertEqual((output / 'discovery/activation-review.yml').read_bytes(), before)
        backup = self.work / 'backed-up-input.yml'
        backup.write_text(yaml.safe_dump(self.values))
        fresh_values = yaml.safe_load(backup.read_text())
        fresh_values['workspace_run'] = uuid.uuid4().hex[:16]
        rebuilt, fresh, _ = self.build(fresh_values)
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stdout + rebuilt.stderr)
        fresh_manifest = yaml.safe_load((fresh / 'discovery/activation-review.yml').read_text())
        self.assertEqual(fresh_manifest['pilot_review_hashes'], manifest['pilot_review_hashes'])
        for name in manifest['pilot_review_hashes']:
            self.assertEqual((fresh / 'discovery' / name).read_bytes(), (output / 'discovery' / name).read_bytes())
        self.assertEqual(evidence.read_text(), 'preserve me')
        gated = subprocess.run(['bash', str(fresh / 'session.sh'), 'start'], capture_output=True, text=True)
        self.assertEqual(gated.returncode, 2)
        self.assertFalse(list((fresh / 'discovery').glob('*-output-*.log')))
        mockbin = self.work / 'mockbin'; mockbin.mkdir()
        caller = mockbin / 'ansible-playbook'
        caller.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$TEST_ARGV"\nexit "${TEST_RC:-0}"\n')
        caller.chmod(0o700)
        for action, playbook, flag, code in [
            ('start','activate.yml','pilot_activation_approved=true',0),
            ('stop','shutdown.yml','pilot_shutdown_approved=true',0),
            ('preserve','preserve-session.yml','workspace_preservation_approved=true',12)]:
            argv_path = self.work / (action + '-argv')
            invoked = subprocess.run(['bash', str(fresh / 'session.sh'), action, 'approved'],
                env={**os.environ,'PATH':str(mockbin)+':'+os.environ['PATH'],
                     'TEST_ARGV':str(argv_path),'TEST_RC':str(code)},capture_output=True,text=True)
            self.assertEqual(invoked.returncode,code,invoked.stdout+invoked.stderr)
            args = argv_path.read_text().splitlines()
            self.assertIn(str(self.pilot / playbook),args)
            self.assertIn('--ask-become-pass',args)
            self.assertIn(flag,args)
            summary = next((fresh / 'discovery').glob(action+'-output-*.summary.txt'))
            self.assertIn('Exit status: '+str(code),summary.read_text())
            self.assertEqual(summary.stat().st_mode & 0o777,0o600)

    def test_invalid_inputs_leave_node_and_review_absent(self):
        cases = [dict(pxe_pilot_mac='UNCONFIGURED'), dict(workspace_node='../escape'),
                 dict(workspace_menu_state='either'), dict(workspace_lifetime_seconds=3600),
                 dict(workspace_metadata_source='UNCONFIGURED'),
                 dict(pxe_output_dir='/srv/not-a-review'), dict(workspace_run_dir='/srv/not-a-workspace'),
                 dict(workspace_lifetime_seconds=False),
                 dict(workspace_menu_state='stock', workspace_stock_menu_sha256='bad')]
        for change in cases:
            with self.subTest(change=change):
                values = {**self.values, 'workspace_run': uuid.uuid4().hex[:16], **change}
                if '/' in values['workspace_node']:
                    source = self.work / 'invalid.yml'; source.write_text(yaml.safe_dump(values))
                    result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local',
                        str(self.pilot / 'workspace.yml'), '-e', '@'+str(source)], env=self.env,
                        capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse((self.repo / 'pxe/local').exists())
                else:
                    result, output, review = self.build(values)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())
                    self.assertFalse(review.exists())

    def test_symlinked_ancestor_does_not_write_outside_workspace(self):
        other = self.work / 'outside'; other.mkdir()
        (self.repo / 'pxe/local').symlink_to(other, target_is_directory=True)
        result, _, review = self.build(self.values)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(other.iterdir()), [])
        self.assertFalse(review.exists())

    def test_builder_and_renderer_cannot_invoke_live_operations(self):
        allowed = {'ansible.builtin.assert', 'ansible.builtin.stat', 'ansible.builtin.file',
                   'ansible.builtin.template', 'ansible.builtin.copy', 'ansible.builtin.set_fact',
                   'ansible.builtin.debug', 'ansible.builtin.command'}
        plays = yaml.safe_load((ROOT / 'workspace.yml').read_text())
        self.assertEqual(plays[1], {'import_playbook': 'prepare.yml'})
        for play in [plays[0], plays[2]]:
            self.assertEqual(play['hosts'], 'localhost')
            self.assertFalse(play['become'])
            self.assertFalse(play['gather_facts'])
            for task in play['tasks']:
                modules = {k for k in task if k.startswith('ansible.')}
                self.assertEqual(len(modules), 1)
                self.assertTrue(modules <= allowed)
                if 'ansible.builtin.command' in task:
                    self.assertEqual(task['ansible.builtin.command']['argv'], ['id', '-u'])

if __name__ == '__main__': unittest.main()
