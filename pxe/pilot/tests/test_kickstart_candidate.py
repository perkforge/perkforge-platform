"""Static specimen checks only; never run Kickstart scripts or boot an installer."""
from pathlib import Path
import re
import unittest
from jinja2 import Environment, StrictUndefined, UndefinedError

CANDIDATE = Path(__file__).resolve().parents[2] / 'kickstart/rhel10.ks.j2'

class KickstartCandidate(unittest.TestCase):
    def setUp(self):
        self.text=CANDIDATE.read_text()
        self.environment=Environment(undefined=StrictUndefined)
        self.fixture=dict(timezone='Etc/UTC',ntp_server='time.example.invalid',
            installation_source_url='http://192.0.2.10/rhel10/',boot_nic_mac='02:00:00:00:00:11',
            hostname='fixture.invalid',bootstrap_username='fixture',
            bootstrap_public_key='ssh-ed25519 RFC8032_DUMMY_PLACEHOLDER',
            disk_stable_id='UNCONFIGURED',disk_serial='UNCONFIGURED',disk_capacity_bytes='UNCONFIGURED')

    def test_unconditional_abort_and_no_active_storage_commands(self):
        rendered=self.environment.from_string(self.text).render(**self.fixture)
        pre=rendered.split('%pre --erroronfail',1)[1].split('%end',1)[0]
        self.assertRegex(pre,r'(?m)^exit 1$')
        self.assertNotIn('if ',pre)
        active='\n'.join(line for line in rendered.splitlines() if not line.lstrip().startswith('#'))
        self.assertNotRegex(active,r'(?m)^(clearpart|zerombr|part|partition|autopart|volgroup|logvol|bootloader|reboot)\b')
        self.assertNotRegex(active,r'--(password|iscrypted)|NOPASSWD|inst\.ks=|--noverifyssl')
        self.assertIn('UNCONFIGURED',rendered)

    def test_missing_inventory_is_not_silently_defaulted(self):
        with self.assertRaises(UndefinedError):self.environment.from_string(self.text).render()
        for name in self.fixture:
            missing=dict(self.fixture);missing.pop(name)
            with self.subTest(name=name), self.assertRaises(UndefinedError):
                self.environment.from_string(self.text).render(**missing)

    def test_current_vendor_source_time_and_network_shape(self):
        rendered=self.environment.from_string(self.text).render(**self.fixture)
        active='\n'.join(line for line in rendered.splitlines() if not line.lstrip().startswith('#'))
        self.assertIn('url --url="http://192.0.2.10/rhel10/"',active)
        self.assertIn('timezone Etc/UTC --utc',active)
        self.assertIn('timesource --ntp-server time.example.invalid',active)
        self.assertIn('--device=02:00:00:00:00:11',active)
        self.assertNotRegex(active,r'--isUtc|--ntpservers|--nontp|(?m:^(authconfig|method|vnc)\b)')

    def test_known_package_intent_and_no_embedded_private_identifiers(self):
        for package in ['openssh-server','sudo','python3','kernel-modules-extra']:
            self.assertRegex(self.text,r'(?m)^'+re.escape(package)+r'$')
        self.assertNotRegex(self.text,r'192\.168\.|/home/corey|PRIVATE KEY-----')
        self.assertIn('rootpw --lock',self.text)
        self.assertIn('sshkey --username=',self.text)
