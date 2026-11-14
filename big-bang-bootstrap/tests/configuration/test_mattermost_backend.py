"""Offline dedicated backend contracts; no credentials or cluster access."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / 'big-bang-bootstrap/configuration/packages/mattermost'

class MattermostBackend(unittest.TestCase):
    def test_files_are_dedicated_and_portable(self):
        pvc = yaml.safe_load((MODULE/'backend/files-pvc.yaml').read_text())
        self.assertEqual(pvc['metadata'], {'name':'mattermost-files','namespace':'mattermost'})
        self.assertEqual(pvc['spec']['accessModes'], ['ReadWriteOnce'])
        self.assertEqual(pvc['spec']['resources']['requests']['storage'], '10Gi')
        self.assertNotIn('storageClassName', pvc['spec'])
        values = yaml.safe_load((MODULE/'backend/files-values.yaml').read_text())['addons']['mattermost']
        patch = values['postRenderers'][0]['kustomize']['patches'][0]
        self.assertEqual(patch['target']['kind'], 'Mattermost')
        self.assertEqual(yaml.safe_load(patch['patch']), [{'op':'replace','path':'/spec/fileStore','value':{'externalVolume':{'volumeClaimName':'mattermost-files'}}}])
        self.assertFalse(values['values']['minio']['install'])
        self.assertNotIn('enabled', values)
        self.assertNotIn('flux', values)

    def test_database_uses_native_existing_secret_and_image_contract(self):
        values = yaml.safe_load((MODULE/'backend/database-values.yaml').read_text())['addons']['mattermost']['values']
        pg = values['postgresql']
        self.assertTrue(pg['install'])
        self.assertNotIn('image', pg)
        self.assertEqual(pg['auth']['existingSecret'], 'mattermost-postgresql-auth')
        self.assertEqual(pg['auth']['username'], '')
        self.assertEqual(pg['primary']['persistence']['size'], '8Gi')
        self.assertEqual(pg['primary']['initdb']['args'], '--auth-host=scram-sha-256')
        self.assertEqual(pg['primary']['containerSecurityContext']['runAsUser'], 1001)
        self.assertIn('NOSUPERUSER NOCREATEDB NOCREATEROLE', pg['primary']['initdb']['scripts']['10-mattermost.sql'])
        self.assertIn('pg_isready', str(pg['primary']['customReadinessProbe']))
        self.assertNotIn('.initialized', str(pg['primary']['customReadinessProbe']))
        self.assertEqual(values['database']['secret'], 'mattermost-database')

    def test_lab_sizing_is_explicit_opt_in(self):
        candidate = yaml.safe_load((MODULE/'candidate-values.yaml').read_text())
        self.assertFalse(candidate['addons']['mattermost']['enabled'])
        self.assertEqual(candidate['addons']['mattermost']['values']['resources']['requests']['cpu'], 2)
        lab = yaml.safe_load((MODULE/'backend/lab-resources-values.yaml').read_text())
        self.assertEqual(lab['addons']['mattermost']['values']['resources']['requests'], {'cpu':'500m','memory':'1Gi'})
        self.assertNotIn('nodeSelector', lab['addons']['mattermost']['values'])

if __name__ == '__main__': unittest.main()
