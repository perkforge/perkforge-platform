"""Stateful local-file DNS fixtures; fake executables, no host/network/sudo use."""
import hashlib
import os
from pathlib import Path
import pwd
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / 'infrastructure/ansible/tasks/maintain-lab-dns.yml'
PLAY = ROOT / 'infrastructure/ansible/playbooks/maintain-lab-dns.yml'
FAKE = '''#!/usr/bin/python3
import os,sys,pathlib
name=pathlib.Path(sys.argv[0]).name;mode=os.environ.get('DNS_FIXTURE_MODE','')
config=pathlib.Path(os.environ['DNS_FIXTURE_CONFIG']);calls=pathlib.Path(os.environ['DNS_FIXTURE_CALLS'])
with calls.open('a') as f:f.write(name+' '+' '.join(sys.argv[1:])+'\\n')
if name=='dnsmasq':
 p=pathlib.Path(next(x.split('=',1)[1] for x in sys.argv if x.startswith('--conf-file=')))
 sys.exit(1 if mode=='validate' and 'gitlab-objects' in p.read_text() else 0)
if name=='restorecon':sys.exit(0)
if name=='systemctl':
 assert sys.argv[2]=='perkforge-lab-dns'
 if sys.argv[1]=='show':
  print('FragmentPath='+os.environ['DNS_FIXTURE_UNIT'])
  print('DropInPaths='+('/unmanaged.conf' if mode=='dropin' else ''))
  print('NeedDaemonReload='+('yes' if mode=='reload' else 'no'));sys.exit(0)
 if sys.argv[1]=='is-active':print('active');sys.exit(0)
 assert sys.argv[1]=='restart'
 flag=config.parent/'restart-failed'
 if mode=='restart' and not flag.exists():flag.touch();sys.exit(1)
 if mode=='foreign':config.write_text(config.read_text()+'# concurrent edit\\n');sys.exit(1)
 sys.exit(0)
if name=='dig':
 host=sys.argv[2]
 if host=='example.com':print('93.184.216.34');sys.exit(0)
 if mode=='verify' and host.startswith('gitlab'):sys.exit(0)
 for line in config.read_text().splitlines():
  if line.startswith('host-record='+host+','):print(line.split(',')[1]);break
 sys.exit(0)
sys.exit(99)
'''


class DNSMaintenance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dns-maintenance-fixture-')
        self.path = Path(self.tmp.name)
        self.config = self.path / 'dns.conf'
        self.unit = self.path / 'dns.service'
        self.backup = self.path / 'backups'
        self.calls = self.path / 'calls'
        self.bin = self.path / 'bin'
        self.bin.mkdir()
        for name in ('systemctl', 'dnsmasq', 'dig', 'restorecon'):
            p = self.bin / name
            p.write_text(FAKE)
            p.chmod(0o700)
        self.original = ('# owned DNS fixture; preserve this comment\nport=53\n'
                         'listen-address=10.0.0.1\nbind-dynamic\nno-resolv\n'
                         'server=10.0.0.254\n' + ''.join(
                             'host-record='+x+'.perkforge.home.arpa,10.0.0.2\n'
                             for x in ('headlamp', 'keycloak', 'rancher', 'openbao')))
        self.config.write_text(self.original)
        self.config.chmod(0o644)
        self.unit_bytes = (ROOT / 'infrastructure/ansible/templates/lab-dns.service.j2').read_text()
        self.unit.write_text(self.unit_bytes)
        self.unit.chmod(0o644)
        self.digest = hashlib.sha256(self.original.encode()).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def run_fixture(self, mode='', digest=None, scope='gitlab-dns-records-v1'):
        variables = {'lab_dns_maintenance_scope': scope, 'lab_dns_config': str(self.config), 'lab_dns_unit': str(self.unit),
                     'lab_dns_backup': str(self.backup),
                     'lab_dns_owner': pwd.getpwuid(os.getuid()).pw_name,
                     'lab_dns_binary': str(self.bin / 'dnsmasq'),
                     'lab_dns_unit_expected': self.unit_bytes,
                     'lab_dns_server_ip': '10.0.0.1', 'lab_dns_ingress_ip': '10.0.0.2',
                     'lab_dns_maintenance_expected_sha256': digest or self.digest}
        wrapper = self.path / 'fixture.yaml'
        wrapper.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
            'gather_facts': False, 'vars': variables,
            'tasks': [{'ansible.builtin.include_tasks': str(TASK)}]}]))
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(wrapper)],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, 'PATH': str(self.bin)+':'+os.environ['PATH'],
                 'DNS_FIXTURE_CONFIG': str(self.config), 'DNS_FIXTURE_CALLS': str(self.calls),
                 'DNS_FIXTURE_UNIT': str(self.unit),
                 'DNS_FIXTURE_MODE': mode, 'ANSIBLE_LOCAL_TEMP': str(self.path/'local'),
                 'ANSIBLE_REMOTE_TEMP': str(self.path/'remote')})

    def restarts(self):
        return self.calls.read_text().count('systemctl restart ') if self.calls.exists() else 0

    def test_add_repeat_preserve_base_and_private_backup(self):
        first = self.run_fixture()
        self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
        final = self.config.read_text()
        self.assertTrue(final.startswith(self.original))
        for name in ('gitlab', 'gitlab-objects'):
            self.assertEqual(final.count('host-record='+name+'.perkforge.home.arpa,10.0.0.2'), 1)
        self.assertEqual(self.unit.read_text(), self.unit_bytes)
        saved = self.backup / (self.digest+'.conf')
        self.assertEqual(saved.read_text(), self.original)
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.backup.stat().st_mode & 0o777, 0o700)
        repeat = self.run_fixture()
        self.assertEqual(repeat.returncode, 0, repeat.stdout+repeat.stderr)
        self.assertIn('changed=0', repeat.stdout)
        self.assertEqual(self.restarts(), 1)
        self.assertEqual(self.config.read_text(), final)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_nextcloud_preserves_six_existing_records_and_is_idempotent(self):
        self.original += ''.join('host-record='+name+'.perkforge.home.arpa,10.0.0.2\n'
                                 for name in ('gitlab','gitlab-objects'))
        self.config.write_text(self.original)
        self.digest = hashlib.sha256(self.original.encode()).hexdigest()
        first = self.run_fixture(scope='nextcloud-dns-record-v1')
        self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
        final = self.config.read_text()
        self.assertTrue(final.startswith(self.original))
        self.assertEqual(final.count('host-record=nextcloud.perkforge.home.arpa,10.0.0.2'), 1)
        self.assertEqual((self.backup/(self.digest+'.conf')).read_text(), self.original)
        repeat = self.run_fixture(scope='nextcloud-dns-record-v1')
        self.assertEqual(repeat.returncode, 0, repeat.stdout+repeat.stderr)
        self.assertIn('changed=0', repeat.stdout)
        self.assertEqual(self.restarts(), 1)

    def test_nextcloud_restart_failure_restores_all_six_records(self):
        self.original += ''.join('host-record='+name+'.perkforge.home.arpa,10.0.0.2\n'
                                 for name in ('gitlab','gitlab-objects'))
        self.config.write_text(self.original)
        self.digest = hashlib.sha256(self.original.encode()).hexdigest()
        r = self.run_fixture('restart', scope='nextcloud-dns-record-v1')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('original configuration restored', r.stdout)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertEqual(self.restarts(), 2)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_nextcloud_requires_existing_gitlab_records(self):
        r = self.run_fixture(scope='nextcloud-dns-record-v1')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.restarts(), 0)

    def test_drift_and_foreign_unit_refused_before_backup_or_write(self):
        self.config.write_text(self.original+'# unreviewed change\n')
        r = self.run_fixture()
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.backup.exists())
        self.config.write_text(self.original)
        self.unit.write_text('unmanaged unit\n')
        r = self.run_fixture()
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.restarts(), 0)

    def test_existing_target_record_is_not_adopted(self):
        text = self.original+'host-record=gitlab.perkforge.home.arpa,10.0.0.99\n'
        self.config.write_text(text)
        r = self.run_fixture(digest=hashlib.sha256(text.encode()).hexdigest())
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.config.read_text(), text)
        self.assertFalse(self.backup.exists())

    def test_dropins_and_stale_loaded_unit_are_refused(self):
        for mode in ('dropin', 'reload'):
            with self.subTest(mode=mode):
                r = self.run_fixture(mode)
                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(self.config.read_text(), self.original)
                self.assertFalse(self.backup.exists())
                self.assertEqual(self.restarts(), 0)

    def test_invalid_candidate_does_not_write_or_restart(self):
        r = self.run_fixture('validate')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertEqual(self.restarts(), 0)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_existing_lock_is_not_removed_or_reused(self):
        self.backup.mkdir(mode=0o700)
        lock = self.backup/'maintenance.lock'
        lock.mkdir(mode=0o700)
        (lock/'owner').write_text('another operation')
        r = self.run_fixture()
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((lock/'owner').read_text(), 'another operation')
        self.assertEqual(self.config.read_text(), self.original)
        self.assertEqual(self.restarts(), 0)

    def test_restart_failure_restores_original_and_reports_failure(self):
        r = self.run_fixture('restart')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('original configuration restored', r.stdout)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertEqual(self.unit.read_text(), self.unit_bytes)
        self.assertEqual(self.restarts(), 2)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_answer_failure_restores_original(self):
        r = self.run_fixture('verify')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertEqual(self.restarts(), 2)

    def test_rollback_never_overwrites_concurrent_edit(self):
        r = self.run_fixture('foreign')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('# concurrent edit', self.config.read_text())
        self.assertEqual(self.restarts(), 1)
        self.assertEqual((self.backup/(self.digest+'.conf')).read_text(), self.original)

    def test_default_check_and_unreviewed_apply_do_not_contact_hosts(self):
        marker = self.path/'contacted'
        for name in ('ssh', 'gh', 'sudo'):
            p = self.bin/name
            p.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\nexit 99\n')
            p.chmod(0o700)
        env = {**os.environ, 'PATH': str(self.bin)+':'+os.environ['PATH'],
               'ANSIBLE_LOCAL_TEMP': str(self.path/'local'),
               'ANSIBLE_REMOTE_TEMP': str(self.path/'remote')}
        for flags, code in (([], 0), (['--check','-e','lab_dns_maintenance_apply=true'], 0),
                            (['-e','lab_dns_maintenance_apply=true'], 2)):
            r = subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY),*flags],
                               env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(r.returncode, code, r.stdout+r.stderr)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
