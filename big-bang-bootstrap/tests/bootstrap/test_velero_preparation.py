"""Pinned chart compatibility for the small, opt-in Velero baseline."""
import os
import importlib.util
from pathlib import Path
import shutil
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/packages/velero'

class VeleroBaselineInputs(unittest.TestCase):
    def test_url_and_cron_verifier_rejects_malformed_or_out_of_range_inputs(self):
        spec = importlib.util.spec_from_file_location('verify_velero_inputs', PACKAGE / 'verify-inputs.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        valid = {'endpoint': 'https://s3.us-east-2.amazonaws.com', 'prefix': 'cluster/tenant', 'cron': '0 */6 * * *'}
        module.verify(valid)
        for endpoint in ('https://a.internal:0', 'https://a.internal:65536', 'https://-bad.internal',
                         'https://bad..internal', 'https://a.internal:', 'https://a.internal/path',
                         'https://user:pass@a.internal', 'http://a.internal', 'https://999.999.999.999'):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                module.verify({**valid, 'endpoint': endpoint})
        for cron in ('99 99 99 99 99', '* * 0 * *', '* * * 13 *', '* * * * 8',
                     '*/0 * * * *', '60 * * * *', '5-2 * * * *', '@hourly', 'a * * * *'):
            with self.subTest(cron=cron), self.assertRaises(ValueError):
                module.verify({**valid, 'cron': cron})



@unittest.skipUnless(os.environ.get('VELERO_CHART_SOURCE') and os.environ.get('PREFLIGHT_SOURCES_DIR')
                     and shutil.which('helm'), 'exact checks require pinned Velero/Big Bang fixtures and Helm')
class VeleroPinnedChart(unittest.TestCase):
    def test_actual_wrapper_pins_and_disabled_data_movement_values(self):
        chart = Path(os.environ['VELERO_CHART_SOURCE']) / 'chart'
        source = Path(os.environ['PREFLIGHT_SOURCES_DIR']) / 'bigbang/chart'
        evidence = yaml.safe_load((PACKAGE / 'compatibility.yaml').read_text())
        metadata = yaml.safe_load((chart / 'Chart.yaml').read_text())
        self.assertEqual(metadata['version'], evidence['chart'])
        self.assertEqual(metadata['appVersion'], evidence['velero'])
        upstream = next(d for d in metadata['dependencies'] if d['name'] == 'velero')
        self.assertEqual(upstream['version'], evidence['upstream_chart'])
        values = yaml.safe_load((chart / 'values.yaml').read_text())
        self.assertEqual(values['upstream']['image']['tag'], 'v' + evidence['velero'])
        self.assertEqual(values['upstream']['initContainers'][0]['image'].split(':')[-1], 'v' + evidence['aws_plugin'])
        umbrella = yaml.safe_load((source / 'values.yaml').read_text())
        self.assertEqual(umbrella['addons']['velero']['git']['tag'], evidence['chart'])
        self.assertFalse(umbrella['addons']['velero']['enabled'])
        candidate = yaml.safe_load((PACKAGE / 'candidate-values.yaml').read_text())['addons']['velero']['values']
        from fixtures.render_helpers import helm
        objects = helm(chart, 'velero', 'velero', [yaml.safe_dump(candidate)])
        kinds = {obj['kind'] for obj in objects}
        self.assertFalse(kinds & {'VolumeSnapshotClass', 'BackupStorageLocation', 'VolumeSnapshotLocation',
                                 'Schedule', 'Backup', 'Restore', 'DaemonSet', 'ClusterRole', 'ClusterRoleBinding'})
        deployment = next(obj for obj in objects if obj['kind'] == 'Deployment')
        arguments = deployment['spec']['template']['spec']['containers'][0]['args']
        self.assertIn('--default-snapshot-move-data=true', arguments)
        self.assertIn('--uploader-type=kopia', arguments)
        # Native render reproduces why blindly enabling CSI is not a local configuration.
        candidate['upstream']['configuration']['features'] = 'EnableCSI'
        api = tuple(part for name in ('VolumeSnapshot', 'VolumeSnapshotClass', 'VolumeSnapshotContent')
                    for part in ('--api-versions', 'snapshot.storage.k8s.io/v1/' + name))
        objects = helm(chart, 'velero', 'velero', [yaml.safe_dump(candidate)], api)
        snapshot = next(obj for obj in objects if obj['kind'] == 'VolumeSnapshotClass')
        self.assertEqual(snapshot['driver'], 'ebs.csi.aws.com')
        self.assertEqual(snapshot['deletionPolicy'], 'Delete')


if __name__ == '__main__':
    unittest.main()
