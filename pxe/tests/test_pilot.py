"""Offline local rendering/parser checks only: no daemon, socket, media or nft calls."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1] / 'transport'

class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pxe-pilot-test-')
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.output = self.work / 'review'
        self.env = {**os.environ, 'ANSIBLE_LOCAL_TEMP': str(self.work / 'local'),
                    'ANSIBLE_REMOTE_TEMP': str(self.work / 'remote'), 'ANSIBLE_NOCOLOR': '1'}
        self.values = dict(pxe_interface='fixture0', pxe_server_ip='192.0.2.10',
            pxe_pilot_ip='192.0.2.11', pxe_pilot_mac='02:00:00:00:00:11',
            pxe_network='192.0.2.0', pxe_netmask='255.255.255.0',
            pxe_service_user='nobody', pxe_service_group='nogroup',
            pxe_http_user='www-data', pxe_http_group='www-data',
            pxe_tftp_ownership_policy='root-readonly',
            pxe_output_dir=str(self.output), pxe_media_layout_reviewed=True,
            pxe_boot_candidates_reviewed=True, pxe_csa=7,
            pxe_efi_entry='fixture/ENTRY.EFI', pxe_grub_config_relative='fixture/grub.cfg',
            pxe_kernel_relative='fixture/vmlinuz', pxe_initrd_relative='fixture/initrd.img',
            pxe_linux_command='linuxefi', pxe_initrd_command='initrdefi')

    def render(self, values):
        variables = self.work / 'fixture.yml'
        variables.write_text(yaml.safe_dump(values))
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(ROOT / 'prepare.yml'),
                               '-e', '@' + str(variables)], capture_output=True, text=True,
                              timeout=30, env=self.env)

    def test_default_missing_inputs_create_no_outputs(self):
        result = self.render({'pxe_output_dir': str(self.output)})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_unsafe_inputs_create_no_outputs(self):
        for changes in [dict(pxe_interface='lo'), dict(pxe_http_user='nobody'),
                        dict(pxe_tftp_ownership_policy='UNCONFIGURED'), dict(pxe_pilot_mac='ff:ff:ff:ff:ff:ff'),
                        dict(pxe_pilot_ip='192.0.2.999'), dict(pxe_pilot_ip='198.51.100.11'),
                        dict(pxe_efi_entry='../escape.EFI'), dict(pxe_media_layout_reviewed=False),
                        dict(pxe_boot_candidates_reviewed=False), dict(pxe_csa='UNCONFIGURED'), dict(pxe_http_port='8080\n'),
                        dict(pxe_output_dir='/etc/dnsmasq.d/pilot')]:
            with self.subTest(changes=changes):
                result = self.render({**self.values, **changes})
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())

    def test_fixture_render_and_available_native_parsers(self):
        result = self.render(self.values)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertEqual({p.name for p in self.output.iterdir()},
                         {'dnsmasq.conf', 'nginx.conf', 'grub.cfg', 'ingress.nft', 'review.txt'})
        for path in self.output.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn('UNCONFIGURED', path.read_text())
        self.assertIn('NODE-FACING RUNTIME EVIDENCE PENDING', (self.output / 'review.txt').read_text())
        dns = (self.output / 'dnsmasq.conf').read_text()
        self.assertIn('dhcp-range=192.0.2.0,proxy,255.255.255.0', dns)
        self.assertIn('dhcp-ignore=tag:!pilot', dns)
        self.assertIn('enable-tftp=fixture0', dns)
        active_dns_lines = [x for x in dns.splitlines() if not x.startswith('#')]
        self.assertNotIn('tftp-secure', active_dns_lines)
        for forbidden in ['dhcp-authoritative', 'conf-dir=', 'dhcp-option=', 'enable-ra']:
            self.assertNotIn(forbidden, dns)
        grub = (self.output / 'grub.cfg').read_text()
        self.assertIn('set timeout=-1', grub)
        self.assertNotIn('inst.ks', grub)
        self.assertNotIn('autopart', grub)
        http = (self.output / 'nginx.conf').read_text()
        self.assertIn('listen 192.0.2.10:8080;', http)
        self.assertIn('user www-data www-data;', http)
        self.assertIn('pid /run/perkforge-pxe-pilot/http/nginx.pid;', http)
        self.assertIn('client_body_temp_path /run/perkforge-pxe-pilot/http/client-body;', http)
        self.assertIn('error_log /var/log/perkforge-pxe-pilot/http/nginx-error.log warn;', http)
        self.assertIn('pid-file=/run/perkforge-pxe-pilot/dnsmasq/dnsmasq.pid', dns)
        self.assertIn('dhcp-leasefile=/run/perkforge-pxe-pilot/dnsmasq/leases', dns)
        self.assertIn('lock_file /run/perkforge-pxe-pilot/http/nginx.lock;', http)
        self.assertIn('log-facility=/var/log/perkforge-pxe-pilot/dnsmasq/dnsmasq.log', dns)
        self.assertIn('allow 192.0.2.11;', http)
        self.assertIn('deny all;', http)
        self.assertNotIn('include ', http)
        rules = (self.output / 'ingress.nft').read_text()
        self.assertIn('policy accept;', rules)
        self.assertIn('{ 0.0.0.0, 192.0.2.11 }', rules)
        self.assertIn('meta nfproto ipv6 udp dport', rules)
        self.assertIn('ip daddr != 192.0.2.10 drop', rules)
        self.assertNotIn('flush ruleset', rules.replace('# REVIEW ONLY. Never flush the ruleset', ''))
        self.assertNotIn('table ip ', rules)
        dnsmasq = shutil.which('dnsmasq') or '/usr/sbin/dnsmasq'
        if Path(dnsmasq).exists():
            check = subprocess.run([dnsmasq, '--test', '--conf-file=' + str(self.output / 'dnsmasq.conf')],
                                   text=True, capture_output=True, timeout=15)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        grub_check = shutil.which('grub-script-check')
        if grub_check:
            check = subprocess.run([grub_check, str(self.output / 'grub.cfg')], text=True,
                                   capture_output=True, timeout=15)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        # nft is intentionally never called, even with --check; nginx is not launched.
        second = self.render(self.values)
        self.assertNotEqual(second.returncode, 0, 'Never overwrite an existing review directory')

    def test_renderer_has_only_local_file_and_validation_modules(self):
        play = yaml.safe_load((ROOT / 'prepare.yml').read_text())[0]
        self.assertEqual(play['hosts'], 'localhost')
        self.assertFalse(play['become'])
        self.assertFalse(play['gather_facts'])
        allowed = {'ansible.builtin.assert', 'ansible.builtin.stat',
                   'ansible.builtin.file', 'ansible.builtin.template'}
        for task in play['tasks']:
            modules = {k for k in task if k.startswith('ansible.')}
            self.assertEqual(len(modules), 1)
            self.assertTrue(modules <= allowed, modules)

if __name__ == '__main__':
    unittest.main()
