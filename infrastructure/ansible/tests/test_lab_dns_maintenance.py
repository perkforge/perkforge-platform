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
targets=os.environ['DNS_FIXTURE_TARGETS'].split(',')
config=pathlib.Path(os.environ['DNS_FIXTURE_CONFIG']);calls=pathlib.Path(os.environ['DNS_FIXTURE_CALLS'])
with calls.open('a') as f:f.write(name+' '+' '.join(sys.argv[1:])+'\\n')
if name=='dnsmasq':
 p=pathlib.Path(next(x.split('=',1)[1] for x in sys.argv if x.startswith('--conf-file=')))
 sys.exit(1 if mode=='validate' and any('host-record='+h+'.perkforge.home.arpa,' in p.read_text() for h in targets) else 0)
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
 if host=='example.com':
  if mode!='external':print('192.0.2.80')
  sys.exit(0)
 if mode=='verify' and host in [h+'.perkforge.home.arpa' for h in targets]:sys.exit(0)
 if mode=='preflight' and host=='headlamp.perkforge.home.arpa':sys.exit(0)
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
                 'DNS_FIXTURE_TARGETS': {'nextcloud-dns-record-v1': 'nextcloud',
                     'grafana-dns-record-v1': 'grafana',
                     'portal-dns-record-v1': 'portal',
                     'ntfy-dns-record-v1': 'ntfy',
                     'harbor-dns-record-v1': 'harbor'}.get(scope, 'gitlab,gitlab-objects'),
                 'DNS_FIXTURE_MODE': mode, 'ANSIBLE_LOCAL_TEMP': str(self.path/'local'),
                 'ANSIBLE_REMOTE_TEMP': str(self.path/'remote')})

    def restarts(self):
        return self.calls.read_text().count('systemctl restart ') if self.calls.exists() else 0

    @staticmethod
    def record_block(marker, names):
        return ('\n# BEGIN PerkForge '+marker+' DNS v1\n' + ''.join(
            'host-record='+name+'.perkforge.home.arpa,10.0.0.2\n' for name in names)
            + '# END PerkForge '+marker+' DNS v1\n')

    def test_add_repeat_preserve_base_and_private_backup(self):
        first = self.run_fixture()
        self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
        final = self.config.read_text()
        self.assertEqual(final, self.original+self.record_block('GitLab', ('gitlab', 'gitlab-objects')))
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
        self.assertEqual(final, self.original+self.record_block('Nextcloud', ('nextcloud',)))
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

    def grafana_base(self):
        self.original += ''.join('host-record='+name+'.perkforge.home.arpa,10.0.0.2\n'
                                 for name in ('gitlab','gitlab-objects','nextcloud'))
        self.config.write_text(self.original)
        self.digest = hashlib.sha256(self.original.encode()).hexdigest()

    def test_grafana_preserves_seven_records_and_is_idempotent(self):
        self.grafana_base()
        first = self.run_fixture(scope='grafana-dns-record-v1')
        self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
        final = self.config.read_text()
        self.assertEqual(final, self.original+self.record_block('Grafana', ('grafana',)))
        self.assertTrue(final.startswith(self.original))
        self.assertEqual(final.count('host-record=grafana.perkforge.home.arpa,10.0.0.2'), 1)
        self.assertEqual((self.backup/(self.digest+'.conf')).read_text(), self.original)
        repeat = self.run_fixture(scope='grafana-dns-record-v1')
        self.assertEqual(repeat.returncode, 0, repeat.stdout+repeat.stderr)
        self.assertIn('changed=0', repeat.stdout)
        self.assertEqual(self.restarts(), 1)

    def test_grafana_restart_failure_restores_seven_records(self):
        self.grafana_base()
        result = self.run_fixture('restart', scope='grafana-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertEqual(self.restarts(), 2)

    def test_grafana_missing_prior_records_refuses_without_write(self):
        result = self.run_fixture(scope='grafana-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertFalse(self.backup.exists())

    def harbor_base(self):
        # Preserve actual predecessor block forms, blank lines and unrelated bytes.
        self.original += self.record_block('GitLab', ('gitlab', 'gitlab-objects'))
        self.original += self.record_block('Nextcloud', ('nextcloud',))
        self.original += self.record_block('Grafana', ('grafana',))
        self.original += '# reviewed unrelated comment with trailing spaces  \n\n'
        self.config.write_text(self.original)
        self.digest = hashlib.sha256(self.original.encode()).hexdigest()

    def assert_harbor_queries(self, names, expected_count=1):
        calls = self.calls.read_text().splitlines()
        for name in names:
            for transport in ('+notcp', '+tcp'):
                query = ('dig @10.0.0.1 '+name+'.perkforge.home.arpa A '
                         '+short +time=2 +tries=1 '+transport)
                self.assertEqual(calls.count(query), expected_count, query)

    def test_harbor_exact_add_repeat_preservation_backup_and_udp_tcp(self):
        self.harbor_base()
        result = self.run_fixture(scope='harbor-dns-record-v1')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        expected = (self.original+self.record_block('Harbor', ('harbor',))).encode()
        self.assertEqual(self.config.read_bytes(), expected)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.unit.read_bytes(), self.unit_bytes.encode())
        saved = self.backup/(self.digest+'.conf')
        self.assertEqual(saved.read_bytes(), self.original.encode())
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual(saved.stat().st_uid, os.getuid())
        self.assert_harbor_queries(('harbor',))
        self.assert_harbor_queries(('headlamp', 'keycloak', 'rancher', 'openbao',
                                   'gitlab', 'gitlab-objects', 'nextcloud', 'grafana'), 2)
        calls = self.calls.read_text()
        self.assertEqual(calls.count('dnsmasq --test --conf-file='), 1)
        self.assertEqual(calls.count('restorecon '), 1)
        self.assertEqual(calls.count('dig @10.0.0.1 example.com A '), 2)
        before_repeat = (self.config.stat().st_ino, self.config.stat().st_mtime_ns,
                         saved.stat().st_ino, saved.stat().st_mtime_ns)
        repeat = self.run_fixture(scope='harbor-dns-record-v1')
        self.assertEqual(repeat.returncode, 0, repeat.stdout+repeat.stderr)
        self.assertIn('changed=0', repeat.stdout)
        self.assertEqual(self.restarts(), 1)
        self.assertEqual(self.config.read_bytes(), expected)
        self.assertEqual(saved.read_bytes(), self.original.encode())
        self.assertEqual(before_repeat,
            (self.config.stat().st_ino, self.config.stat().st_mtime_ns,
             saved.stat().st_ino, saved.stat().st_mtime_ns))
        self.assertEqual(self.calls.read_text().count('restorecon '), 1)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_harbor_each_missing_prior_record_is_refused(self):
        self.harbor_base()
        for name in ('headlamp', 'keycloak', 'rancher', 'openbao', 'gitlab',
                     'gitlab-objects', 'nextcloud', 'grafana'):
            with self.subTest(name=name):
                before = self.original.replace('host-record='+name+'.perkforge.home.arpa,10.0.0.2\n', '')
                self.config.write_text(before)
                result = self.run_fixture(scope='harbor-dns-record-v1',
                    digest=hashlib.sha256(before.encode()).hexdigest())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_bytes(), before.encode())
                self.assertFalse(self.backup.exists())
                self.assertEqual(self.restarts(), 0)

    def test_harbor_foreign_record_and_block_are_not_adopted(self):
        self.harbor_base()
        for suffix in (
                'host-record=harbor.perkforge.home.arpa,10.0.0.2\n',
                'host-record=harbor.perkforge.home.arpa,10.0.0.99\n',
                'address=/harbor.perkforge.home.arpa/10.0.0.2\n',
                'cname=harbor.perkforge.home.arpa,grafana.perkforge.home.arpa\n',
                self.record_block('Harbor', ('harbor',)).replace('DNS v1', 'DNS v2')):
            with self.subTest(suffix=suffix):
                before = self.original+suffix
                self.config.write_text(before)
                result = self.run_fixture(scope='harbor-dns-record-v1',
                    digest=hashlib.sha256(before.encode()).hexdigest())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_bytes(), before.encode())
                self.assertFalse(self.backup.exists())
                self.assertEqual(self.restarts(), 0)

    def test_harbor_restart_failure_restores_eight_records_and_reports_failure(self):
        self.harbor_base()
        result = self.run_fixture('restart', scope='harbor-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('original configuration restored', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.unit.read_bytes(), self.unit_bytes.encode())
        self.assertEqual((self.backup/(self.digest+'.conf')).read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 2)
        self.assert_harbor_queries(('headlamp', 'keycloak', 'rancher', 'openbao',
                                   'gitlab', 'gitlab-objects', 'nextcloud', 'grafana'), 2)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_harbor_answer_failure_restores_eight_records(self):
        self.harbor_base()
        result = self.run_fixture('verify', scope='harbor-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('original configuration restored', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 2)
        self.assert_harbor_queries(('headlamp', 'keycloak', 'rancher', 'openbao',
                                   'gitlab', 'gitlab-objects', 'nextcloud', 'grafana'), 3)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_harbor_external_answer_failure_rolls_back(self):
        self.harbor_base()
        result = self.run_fixture('external', scope='harbor-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('original configuration restored', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 2)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_harbor_validation_failure_preserves_config_and_service(self):
        self.harbor_base()
        result = self.run_fixture('validate', scope='harbor-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('before any configuration write', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 0)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_harbor_failed_repeat_never_removes_existing_owned_block(self):
        self.harbor_base()
        before = self.original+self.record_block('Harbor', ('harbor',))
        self.config.write_text(before)
        result = self.run_fixture('verify', scope='harbor-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('before any configuration write', result.stdout)
        self.assertEqual(self.config.read_bytes(), before.encode())
        self.assertEqual(self.restarts(), 0)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_harbor_concurrent_edit_is_never_overwritten_by_rollback(self):
        self.harbor_base()
        result = self.run_fixture('foreign', scope='harbor-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_text(),
                         self.original+self.record_block('Harbor', ('harbor',))+'# concurrent edit\n')
        self.assertEqual(self.restarts(), 1)
        self.assertEqual((self.backup/(self.digest+'.conf')).read_bytes(), self.original.encode())
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_harbor_checksum_and_unit_guards_refuse_before_backup(self):
        self.harbor_base()
        for mode in ('checksum', 'unit', 'dropin', 'reload', 'preflight'):
            with self.subTest(mode=mode):
                before = self.original+('# drift\n' if mode == 'checksum' else '')
                self.config.write_text(before)
                unit = 'foreign unit\n' if mode == 'unit' else self.unit_bytes
                self.unit.write_text(unit)
                result = self.run_fixture(mode, scope='harbor-dns-record-v1')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_bytes(), before.encode())
                self.assertEqual(self.unit.read_text(), unit)
                self.assertFalse(self.backup.exists())
                self.assertEqual(self.restarts(), 0)

    def test_harbor_symlinks_and_wrong_modes_are_refused(self):
        self.harbor_base()
        for target in (self.config, self.unit):
            for mode in ('symlink', 'permissions'):
                with self.subTest(target=target.name, mode=mode):
                    contents = target.read_bytes()
                    if mode == 'symlink':
                        actual = target.with_suffix('.real')
                        target.rename(actual)
                        target.symlink_to(actual)
                    else:
                        target.chmod(0o666)
                    result = self.run_fixture(scope='harbor-dns-record-v1')
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(target.read_bytes(), contents)
                    self.assertFalse(self.backup.exists())
                    self.assertEqual(self.restarts(), 0)
                    if mode == 'symlink':
                        target.unlink()
                        actual.rename(target)
                    else:
                        target.chmod(0o644)

    def test_harbor_busy_lock_is_preserved(self):
        self.harbor_base()
        self.backup.mkdir(mode=0o700)
        lock = self.backup/'maintenance.lock'
        lock.mkdir(mode=0o700)
        (lock/'owner').write_text('another operation')
        result = self.run_fixture(scope='harbor-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((lock/'owner').read_text(), 'another operation')
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertFalse((self.backup/(self.digest+'.conf')).exists())
        self.assertEqual(self.restarts(), 0)

    def test_harbor_foreign_backup_is_not_overwritten(self):
        self.harbor_base()
        self.backup.mkdir(mode=0o700)
        saved = self.backup/(self.digest+'.conf')
        saved.write_text('foreign backup\n')
        saved.chmod(0o600)
        result = self.run_fixture(scope='harbor-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(saved.read_text(), 'foreign backup\n')
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 0)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_unrecognized_scope_is_refused_without_commands(self):
        result = self.run_fixture(scope='arbitrary-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.backup.exists())

    def test_harbor_public_default_check_and_unreviewed_apply_make_no_contact(self):
        marker = self.path/'contacted'
        for name in ('ssh', 'gh', 'sudo', 'dig', 'systemctl', 'dnsmasq', 'restorecon'):
            stub = self.bin/name
            stub.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\nexit 99\n')
            stub.chmod(0o700)
        inventory = self.path/'inventory.yaml'
        inventory.write_text(yaml.safe_dump({'all': {'children': {
            'rke2_servers': {'hosts': {'control-1': {'ansible_host': '192.0.2.1'}}},
            'rke2_agents': {'hosts': {'worker-1': {'ansible_host': '192.0.2.2'},
                                    'worker-2': {'ansible_host': '192.0.2.3'}}},
            # Even an explicitly selected remote target must remain inert.
            'lab_dns_maintenance_server': {'hosts': {'control-1': {}}}}}}))
        env = {**os.environ, 'PATH': str(self.bin)+':'+os.environ['PATH'],
               'ANSIBLE_LOCAL_TEMP': str(self.path/'local'),
               'ANSIBLE_REMOTE_TEMP': str(self.path/'remote')}
        for flags, expected in (([], 0), (['--check'], 0),
                (['--check', '-e', 'lab_dns_maintenance_apply=true'], 0),
                (['-e', 'lab_dns_maintenance_apply=true'], 2)):
            with self.subTest(flags=flags):
                result = subprocess.run(['ansible-playbook', '-i', str(inventory),
                    str(PLAY), '-e', 'lab_dns_maintenance_scope=harbor-dns-record-v1',
                    *flags], env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
                self.assertFalse(marker.exists())
                self.assertFalse(self.backup.exists())

    def portal_base(self):
        # Preserve actual predecessor block forms, blank lines and unrelated bytes.
        self.original += self.record_block('GitLab', ('gitlab', 'gitlab-objects'))
        self.original += self.record_block('Nextcloud', ('nextcloud',))
        self.original += self.record_block('Grafana', ('grafana',))
        self.original += self.record_block('Harbor', ('harbor',))
        self.original += '# reviewed unrelated comment with trailing spaces  \n\n'
        self.config.write_text(self.original)
        self.digest = hashlib.sha256(self.original.encode()).hexdigest()

    def assert_portal_queries(self, names, expected_count=1):
        calls = self.calls.read_text().splitlines()
        for name in names:
            for transport in ('+notcp', '+tcp'):
                query = ('dig @10.0.0.1 '+name+'.perkforge.home.arpa A '
                         '+short +time=2 +tries=1 '+transport)
                self.assertEqual(calls.count(query), expected_count, query)

    def ntfy_base(self, include_portal=False):
        self.portal_base()
        if include_portal:
            self.original += self.record_block('Portal', ('portal',))
        self.config.write_text(self.original)
        self.digest = hashlib.sha256(self.original.encode()).hexdigest()

    def assert_ntfy_queries(self, names, expected_count=1):
        self.assert_portal_queries(names, expected_count)

    def test_ntfy_exact_add_repeat_preservation_backup_and_udp_tcp(self):
        self.ntfy_base()
        result = self.run_fixture(scope='ntfy-dns-record-v1')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        expected = (self.original+self.record_block('Ntfy', ('ntfy',))).encode()
        self.assertEqual(self.config.read_bytes(), expected)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.unit.read_bytes(), self.unit_bytes.encode())
        saved = self.backup/(self.digest+'.conf')
        self.assertEqual(saved.read_bytes(), self.original.encode())
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual(saved.stat().st_uid, os.getuid())
        self.assert_ntfy_queries(('ntfy',))
        self.assert_ntfy_queries(('headlamp', 'keycloak', 'rancher', 'openbao',
                                   'gitlab', 'gitlab-objects', 'nextcloud', 'grafana', 'harbor'), 2)
        calls = self.calls.read_text()
        self.assertEqual(calls.count('dnsmasq --test --conf-file='), 1)
        self.assertEqual(calls.count('restorecon '), 1)
        self.assertEqual(calls.count('dig @10.0.0.1 example.com A '), 2)
        before_repeat = (self.config.stat().st_ino, self.config.stat().st_mtime_ns,
                         saved.stat().st_ino, saved.stat().st_mtime_ns)
        repeat = self.run_fixture(scope='ntfy-dns-record-v1')
        self.assertEqual(repeat.returncode, 0, repeat.stdout+repeat.stderr)
        self.assertIn('changed=0', repeat.stdout)
        self.assertEqual(self.restarts(), 1)
        self.assertEqual(self.config.read_bytes(), expected)
        self.assertEqual(saved.read_bytes(), self.original.encode())
        self.assertEqual(before_repeat,
            (self.config.stat().st_ino, self.config.stat().st_mtime_ns,
             saved.stat().st_ino, saved.stat().st_mtime_ns))
        self.assertEqual(self.calls.read_text().count('restorecon '), 1)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_ntfy_each_missing_prior_record_is_refused(self):
        self.ntfy_base()
        for name in ('headlamp', 'keycloak', 'rancher', 'openbao', 'gitlab',
                     'gitlab-objects', 'nextcloud', 'grafana', 'harbor'):
            with self.subTest(name=name):
                before = self.original.replace('host-record='+name+'.perkforge.home.arpa,10.0.0.2\n', '')
                self.config.write_text(before)
                result = self.run_fixture(scope='ntfy-dns-record-v1',
                    digest=hashlib.sha256(before.encode()).hexdigest())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_bytes(), before.encode())
                self.assertFalse(self.backup.exists())
                self.assertEqual(self.restarts(), 0)

    def test_ntfy_foreign_record_and_block_are_not_adopted(self):
        self.ntfy_base()
        for suffix in (
                'host-record=ntfy.perkforge.home.arpa,10.0.0.2\n',
                'host-record=ntfy.perkforge.home.arpa,10.0.0.99\n',
                'address=/ntfy.perkforge.home.arpa/10.0.0.2\n',
                'cname=ntfy.perkforge.home.arpa,grafana.perkforge.home.arpa\n',
                self.record_block('Ntfy', ('ntfy',)).replace('DNS v1', 'DNS v2')):
            with self.subTest(suffix=suffix):
                before = self.original+suffix
                self.config.write_text(before)
                result = self.run_fixture(scope='ntfy-dns-record-v1',
                    digest=hashlib.sha256(before.encode()).hexdigest())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_bytes(), before.encode())
                self.assertFalse(self.backup.exists())
                self.assertEqual(self.restarts(), 0)

    def test_ntfy_restart_failure_restores_nine_records_and_reports_failure(self):
        self.ntfy_base()
        result = self.run_fixture('restart', scope='ntfy-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('original configuration restored', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.unit.read_bytes(), self.unit_bytes.encode())
        self.assertEqual((self.backup/(self.digest+'.conf')).read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 2)
        self.assert_ntfy_queries(('headlamp', 'keycloak', 'rancher', 'openbao',
                                   'gitlab', 'gitlab-objects', 'nextcloud', 'grafana', 'harbor'), 2)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_ntfy_answer_failure_restores_nine_records(self):
        self.ntfy_base()
        result = self.run_fixture('verify', scope='ntfy-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('original configuration restored', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 2)
        self.assert_ntfy_queries(('headlamp', 'keycloak', 'rancher', 'openbao',
                                   'gitlab', 'gitlab-objects', 'nextcloud', 'grafana', 'harbor'), 3)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_ntfy_optional_portal_bytes_preserved_without_queries(self):
        self.ntfy_base(include_portal=True)
        expected = self.original+self.record_block('Ntfy', ('ntfy',))
        for _ in range(2):
            result = self.run_fixture(scope='ntfy-dns-record-v1')
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertEqual(self.config.read_text(), expected)
            self.assertEqual((self.backup/(self.digest+'.conf')).read_text(), self.original)
        self.assertEqual(self.restarts(), 1)
        self.assertNotIn('portal.perkforge.home.arpa', self.calls.read_text())

    def test_portal_exact_add_repeat_preservation_backup_and_udp_tcp(self):
        self.portal_base()
        result = self.run_fixture(scope='portal-dns-record-v1')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        expected = (self.original+self.record_block('Portal', ('portal',))).encode()
        self.assertEqual(self.config.read_bytes(), expected)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.unit.read_bytes(), self.unit_bytes.encode())
        saved = self.backup/(self.digest+'.conf')
        self.assertEqual(saved.read_bytes(), self.original.encode())
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual(saved.stat().st_uid, os.getuid())
        self.assert_portal_queries(('portal',))
        self.assert_portal_queries(('headlamp', 'keycloak', 'rancher', 'openbao',
                                   'gitlab', 'gitlab-objects', 'nextcloud', 'grafana', 'harbor'), 2)
        calls = self.calls.read_text()
        self.assertEqual(calls.count('dnsmasq --test --conf-file='), 1)
        self.assertEqual(calls.count('restorecon '), 1)
        self.assertEqual(calls.count('dig @10.0.0.1 example.com A '), 2)
        before_repeat = (self.config.stat().st_ino, self.config.stat().st_mtime_ns,
                         saved.stat().st_ino, saved.stat().st_mtime_ns)
        repeat = self.run_fixture(scope='portal-dns-record-v1')
        self.assertEqual(repeat.returncode, 0, repeat.stdout+repeat.stderr)
        self.assertIn('changed=0', repeat.stdout)
        self.assertEqual(self.restarts(), 1)
        self.assertEqual(self.config.read_bytes(), expected)
        self.assertEqual(saved.read_bytes(), self.original.encode())
        self.assertEqual(before_repeat,
            (self.config.stat().st_ino, self.config.stat().st_mtime_ns,
             saved.stat().st_ino, saved.stat().st_mtime_ns))
        self.assertEqual(self.calls.read_text().count('restorecon '), 1)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_portal_each_missing_prior_record_is_refused(self):
        self.portal_base()
        for name in ('headlamp', 'keycloak', 'rancher', 'openbao', 'gitlab',
                     'gitlab-objects', 'nextcloud', 'grafana', 'harbor'):
            with self.subTest(name=name):
                before = self.original.replace('host-record='+name+'.perkforge.home.arpa,10.0.0.2\n', '')
                self.config.write_text(before)
                result = self.run_fixture(scope='portal-dns-record-v1',
                    digest=hashlib.sha256(before.encode()).hexdigest())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_bytes(), before.encode())
                self.assertFalse(self.backup.exists())
                self.assertEqual(self.restarts(), 0)

    def test_portal_foreign_record_and_block_are_not_adopted(self):
        self.portal_base()
        for suffix in (
                'host-record=portal.perkforge.home.arpa,10.0.0.2\n',
                'host-record=portal.perkforge.home.arpa,10.0.0.99\n',
                'address=/portal.perkforge.home.arpa/10.0.0.2\n',
                'cname=portal.perkforge.home.arpa,grafana.perkforge.home.arpa\n',
                self.record_block('Portal', ('portal',)).replace('DNS v1', 'DNS v2')):
            with self.subTest(suffix=suffix):
                before = self.original+suffix
                self.config.write_text(before)
                result = self.run_fixture(scope='portal-dns-record-v1',
                    digest=hashlib.sha256(before.encode()).hexdigest())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_bytes(), before.encode())
                self.assertFalse(self.backup.exists())
                self.assertEqual(self.restarts(), 0)

    def test_portal_restart_failure_restores_nine_records_and_reports_failure(self):
        self.portal_base()
        result = self.run_fixture('restart', scope='portal-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('original configuration restored', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.unit.read_bytes(), self.unit_bytes.encode())
        self.assertEqual((self.backup/(self.digest+'.conf')).read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 2)
        self.assert_portal_queries(('headlamp', 'keycloak', 'rancher', 'openbao',
                                   'gitlab', 'gitlab-objects', 'nextcloud', 'grafana', 'harbor'), 2)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_portal_answer_failure_restores_nine_records(self):
        self.portal_base()
        result = self.run_fixture('verify', scope='portal-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('original configuration restored', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 2)
        self.assert_portal_queries(('headlamp', 'keycloak', 'rancher', 'openbao',
                                   'gitlab', 'gitlab-objects', 'nextcloud', 'grafana', 'harbor'), 3)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_portal_external_answer_failure_rolls_back(self):
        self.portal_base()
        result = self.run_fixture('external', scope='portal-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('original configuration restored', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 2)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_portal_validation_failure_preserves_config_and_service(self):
        self.portal_base()
        result = self.run_fixture('validate', scope='portal-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('before any configuration write', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 0)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_portal_failed_repeat_never_removes_existing_owned_block(self):
        self.portal_base()
        before = self.original+self.record_block('Portal', ('portal',))
        self.config.write_text(before)
        result = self.run_fixture('verify', scope='portal-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('before any configuration write', result.stdout)
        self.assertEqual(self.config.read_bytes(), before.encode())
        self.assertEqual(self.restarts(), 0)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_portal_concurrent_edit_is_never_overwritten_by_rollback(self):
        self.portal_base()
        result = self.run_fixture('foreign', scope='portal-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_text(),
                         self.original+self.record_block('Portal', ('portal',))+'# concurrent edit\n')
        self.assertEqual(self.restarts(), 1)
        self.assertEqual((self.backup/(self.digest+'.conf')).read_bytes(), self.original.encode())
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_portal_checksum_and_unit_guards_refuse_before_backup(self):
        self.portal_base()
        for mode in ('checksum', 'unit', 'dropin', 'reload', 'preflight'):
            with self.subTest(mode=mode):
                before = self.original+('# drift\n' if mode == 'checksum' else '')
                self.config.write_text(before)
                unit = 'foreign unit\n' if mode == 'unit' else self.unit_bytes
                self.unit.write_text(unit)
                result = self.run_fixture(mode, scope='portal-dns-record-v1')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_bytes(), before.encode())
                self.assertEqual(self.unit.read_text(), unit)
                self.assertFalse(self.backup.exists())
                self.assertEqual(self.restarts(), 0)

    def test_portal_symlinks_and_wrong_modes_are_refused(self):
        self.portal_base()
        for target in (self.config, self.unit):
            for mode in ('symlink', 'permissions'):
                with self.subTest(target=target.name, mode=mode):
                    contents = target.read_bytes()
                    if mode == 'symlink':
                        actual = target.with_suffix('.real')
                        target.rename(actual)
                        target.symlink_to(actual)
                    else:
                        target.chmod(0o666)
                    result = self.run_fixture(scope='portal-dns-record-v1')
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(target.read_bytes(), contents)
                    self.assertFalse(self.backup.exists())
                    self.assertEqual(self.restarts(), 0)
                    if mode == 'symlink':
                        target.unlink()
                        actual.rename(target)
                    else:
                        target.chmod(0o644)

    def test_portal_busy_lock_is_preserved(self):
        self.portal_base()
        self.backup.mkdir(mode=0o700)
        lock = self.backup/'maintenance.lock'
        lock.mkdir(mode=0o700)
        (lock/'owner').write_text('another operation')
        result = self.run_fixture(scope='portal-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((lock/'owner').read_text(), 'another operation')
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertFalse((self.backup/(self.digest+'.conf')).exists())
        self.assertEqual(self.restarts(), 0)

    def test_portal_foreign_backup_is_not_overwritten(self):
        self.portal_base()
        self.backup.mkdir(mode=0o700)
        saved = self.backup/(self.digest+'.conf')
        saved.write_text('foreign backup\n')
        saved.chmod(0o600)
        result = self.run_fixture(scope='portal-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(saved.read_text(), 'foreign backup\n')
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertEqual(self.restarts(), 0)
        self.assertFalse((self.backup/'maintenance.lock').exists())

    def test_portal_unrecognized_scope_is_refused_without_commands(self):
        result = self.run_fixture(scope='arbitrary-dns-record-v1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_bytes(), self.original.encode())
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.backup.exists())

    def test_portal_public_default_check_and_unreviewed_apply_make_no_contact(self):
        marker = self.path/'contacted'
        for name in ('ssh', 'gh', 'sudo', 'dig', 'systemctl', 'dnsmasq', 'restorecon'):
            stub = self.bin/name
            stub.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\nexit 99\n')
            stub.chmod(0o700)
        inventory = self.path/'inventory.yaml'
        inventory.write_text(yaml.safe_dump({'all': {'children': {
            'rke2_servers': {'hosts': {'control-1': {'ansible_host': '192.0.2.1'}}},
            'rke2_agents': {'hosts': {'worker-1': {'ansible_host': '192.0.2.2'},
                                    'worker-2': {'ansible_host': '192.0.2.3'}}},
            # Even an explicitly selected remote target must remain inert.
            'lab_dns_maintenance_server': {'hosts': {'control-1': {}}}}}}))
        env = {**os.environ, 'PATH': str(self.bin)+':'+os.environ['PATH'],
               'ANSIBLE_LOCAL_TEMP': str(self.path/'local'),
               'ANSIBLE_REMOTE_TEMP': str(self.path/'remote')}
        for flags, expected in (([], 0), (['--check'], 0),
                (['--check', '-e', 'lab_dns_maintenance_apply=true'], 0),
                (['-e', 'lab_dns_maintenance_apply=true'], 2)):
            with self.subTest(flags=flags):
                result = subprocess.run(['ansible-playbook', '-i', str(inventory),
                    str(PLAY), '-e', 'lab_dns_maintenance_scope=portal-dns-record-v1',
                    *flags], env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
                self.assertFalse(marker.exists())
                self.assertFalse(self.backup.exists())

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
