"""Staged activation checks; no network or live credentials."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('portal_secrets', ROOT/'local-lab/scripts/prepare-portal-secrets.py')
secrets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secrets)

class ActivationTests(unittest.TestCase):
    def test_admission_gate_requires_current_warning_free_type_check(self):
        policy = {'metadata':{'generation':2},'spec':{'failurePolicy':'Fail'},
                  'status':{'observedGeneration':2,'typeChecking':{'expressionWarnings':[]}}}
        binding = {'spec':{'validationActions':['Deny']}}
        self.assertTrue(secrets.admission_ready(policy,binding))
        policy['status']['typeChecking']['expressionWarnings'] = [{'warning':'fixture type error'}]
        self.assertFalse(secrets.admission_ready(policy,binding))
        policy['status']['typeChecking']['expressionWarnings'] = []
        policy['status']['observedGeneration'] = 1
        self.assertFalse(secrets.admission_ready(policy,binding))

    def test_registry_reader_rejects_permissions_and_symlinks(self):
        with tempfile.TemporaryDirectory() as name:
            p = Path(name)/'fixture'
            p.write_text('synthetic only')
            p.chmod(0o600)
            self.assertEqual(secrets.private_file(p),'synthetic only')
            p.chmod(0o644)
            with self.assertRaises(RuntimeError): secrets.private_file(p)
            p.chmod(0o600)
            link = p.with_name('link');link.symlink_to(p)
            with self.assertRaises(OSError): secrets.private_file(link)

    def test_existing_ca_is_used_without_moving_private_authority(self):
        certs = list(yaml.safe_load_all((ROOT/'local-lab/fleet/bundles/local-tls/certificates.yaml').read_text()))
        self.assertEqual(len(certs),2)
        for obj in certs:
            self.assertEqual(obj['kind'],'Certificate')
            self.assertEqual(obj['metadata']['namespace'],'cattle-system')
            self.assertEqual(obj['spec']['issuerRef'],{'name':'rancher','kind':'Issuer'})
            self.assertNotIn('isCA',obj['spec'])
        self.assertEqual({o['spec']['dnsNames'][0] for o in certs},{'portal.local-lab.test','keycloak.local-lab.test'})

    def test_fleet_enrollment_uses_supported_driven_scan_without_mixing_paths(self):
        repo = yaml.safe_load((ROOT/'local-lab/fleet/gitrepos/portal-foundation.yaml').read_text())['spec']
        self.assertNotIn('paths',repo)
        self.assertEqual(repo['bundles'],[{'base':'local-lab/tenant-config','options':'enrollments/home.yaml'}])
        schema=json.loads((ROOT/'local-lab/tests/fixtures/portal/schemas/fleet-0.16.2.json').read_text())
        self.assertIn('bundles',schema['GitRepo']['properties']['spec']['properties'])

    def test_keycloak_startup_retains_limits_and_coordinates_https(self):
        values=yaml.safe_load((ROOT/'local-lab/fleet/bundles/keycloak/values.yaml').read_text())
        self.assertEqual(values['replicas'],1)
        self.assertEqual(values['resources']['limits']['memory'],'1536Mi')
        self.assertEqual(values['ingress']['tls'],[{'hosts':['keycloak.local-lab.test'],'secretName':'keycloak-tls'}])
        self.assertIn('https://keycloak.local-lab.test/auth',values['extraEnv'])
