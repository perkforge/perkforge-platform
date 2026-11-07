"""Native offline Ansible contracts and pinned chart evidence, never live recovery."""
from copy import deepcopy
import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/packages/velero'
EXAMPLE = yaml.safe_load((PACKAGE / 'request.example.yaml').read_text())['velero_request']


def request_fixture(environment='local'):
    request = deepcopy(EXAMPLE)
    for key in request:
        if key.endswith('_ref'):
            request[key] = 'review-record-421'
    request.update(
        approved_namespaces=['tenant-421'], selected_namespaces=['tenant-421'],
        backup_storage_location='reviewed-backups', snapshot_class='reviewed-csi', source_storage_class='reviewed-source',
        restore_storage_class='reviewed-restore', endpoint='https://backup.internal',
        region='us-east-2', bucket='platform-recovery', prefix='cluster-421/tenant-421',
        identity_mode='existing-secret' if environment == 'local' else 'workload-identity',
        schedule_cron='0 */6 * * *', rpo_hours=6, rollback_window_hours=24,
        database_scope='dedicated', database_version='17.6', schema_version='20261101',
        app_image_digest='sha256:' + 'a' * 64, chart_artifact_digest='sha256:' + 'b' * 64,
        app_git_commit='a' * 40, platform_git_commit='b' * 40, enrollment_git_commit='c' * 40,
        restore_backup_name='tenant-421-known-good', restore_target_namespace='tenant-421-recovery',
        approved_restore_namespaces=['tenant-421-recovery'])
    request['local'] = {
        key: ('review-record-422' if key.endswith('_ref') else value)
        for key, value in request['local'].items()}
    request['local'].update(enforced_quota_bytes=1000, reconciled_backup_budget_bytes=1600,
                            snapshot_restore_headroom_bytes=500)
    request['aws'] = {key: 'review-record-423' for key in request['aws']}
    command = {'container': 'app', 'command': ['/bin/true'], 'onError': 'Fail', 'timeout': '30s'}
    request['backup_hooks'] = [{
        'name': 'fixture-consistency', 'includedNamespaces': ['tenant-421'],
        'labelSelector': {'matchLabels': {'app': 'fixture'}},
        'pre': [{'exec': command}], 'post': [{'exec': deepcopy(command)}]}]
    request['restore_hooks'] = [{
        'name': 'fixture-restore', 'includedNamespaces': ['tenant-421-recovery'],
        'labelSelector': {'matchLabels': {'app': 'fixture'}},
        'postHooks': [{'exec': {'container': 'app', 'command': ['/bin/true'],
                               'onError': 'Fail', 'execTimeout': '30s', 'waitTimeout': '2m'}}]}]
    return request


class VeleroPreparation(unittest.TestCase):
    def run_play(self, request=None, environment='local', controls=None, check=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            binary = path / 'bin'; binary.mkdir()
            marker = path / 'called-api'
            for name in ('kubectl', 'velero', 'aws', 'curl', 'ssh'):
                executable = binary / name
                executable.write_text('#!/bin/sh\necho unexpected > "$API_MARKER"\nexit 99\n')
                executable.chmod(0o700)
            out = path / 'output'; out.mkdir(mode=0o700)
            values = {'velero_environment': environment, 'velero_output_dir': str(out)}
            if request is not None:
                values.update(velero_prepare=True, velero_review_recovery=True, velero_request=request)
            values.update(controls or {})
            input_file = path / 'inputs.json'; input_file.write_text(json.dumps(values))
            command = ['ansible-playbook', '-i', 'localhost,', str(PACKAGE / 'prepare.yaml'),
                       '-e', '@' + str(input_file)]
            if check:
                command.append('--check')
            env = {**os.environ, 'KUBECONFIG': '/dev/null', 'API_MARKER': str(marker),
                   'PATH': str(binary) + os.pathsep + os.environ['PATH'],
                   'ANSIBLE_LOCAL_TEMP': str(path / 'ansible-tmp')}
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=45)
            self.assertFalse(marker.exists(), result.stdout + result.stderr)
            output = out / 'velero-review.yaml'
            data = yaml.safe_load(output.read_text()) if output.exists() else None
            if output.exists():
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            return result, data

    def test_default_check_and_profile_examples_are_inert(self):
        for environment in ('local', 'aws'):
            for request, check in ((None, False), (EXAMPLE, True)):
                with self.subTest(environment=environment, check=check):
                    result, output = self.run_play(request, environment, check=check)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn('changed=0', result.stdout)
                    self.assertIsNone(output)

    def test_no_apply_or_schedule_or_tenant_access_switch(self):
        for name, value in (('velero_apply', True), ('velero_schedules_enabled', True),
                            ('velero_tenant_access', True), ('velero_apply', 'false'),
                            ('velero_prepare', 'true')):
            with self.subTest(control=name, value=value):
                result, output = self.run_play(controls={name: value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(output)

    def test_valid_synthetic_profiles_render_one_disabled_contract(self):
        for environment, ttl, driver in (('local', '48h0m0s', 'driver.longhorn.io'),
                                          ('aws', '336h0m0s', 'ebs.csi.aws.com')):
            with self.subTest(environment=environment):
                result, output = self.run_play(request_fixture(environment), environment)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(output['status'], 'disabled-review-only')
                self.assertNotIn('apiVersion', output)
                self.assertNotIn('kind', output)
                addon = output['candidate_values']['addons']['velero']
                self.assertFalse(addon['enabled'])
                self.assertTrue(addon['flux']['suspend'])
                self.assertFalse(addon['values']['upstream']['deployNodeAgent'])
                self.assertEqual(addon['values']['upstream']['schedules'], {})
                self.assertTrue(output['schedule_spec']['paused'])
                self.assertFalse(output['schedule_spec']['useOwnerReferencesInBackup'])
                self.assertEqual(output['backup_spec']['ttl'], ttl)
                self.assertTrue(output['backup_spec']['snapshotMoveData'])
                self.assertEqual(output['backup_spec']['storageLocation'], 'reviewed-backups')
                self.assertEqual(output['backup_annotations']['velero.io/csi-volumesnapshot-class_' + driver], 'reviewed-csi')
                self.assertEqual(output['backup_spec']['excludedResources'], output['restore_spec']['excludedResources'])
                self.assertFalse(output['backup_spec']['includeClusterResources'])
                self.assertFalse(output['backup_spec']['defaultVolumesToFsBackup'])
                self.assertEqual(output['storage_mapping']['driver'], driver)
                self.assertEqual(output['restore_spec']['existingResourcePolicy'], 'none')
                self.assertEqual(output['restore_spec']['hooks']['resources'][0]['includedNamespaces'], ['tenant-421-recovery'])
                self.assertEqual(output['restore_spec']['namespaceMapping'],
                                 {'tenant-421': 'tenant-421-recovery'})
                self.assertEqual(output['recovery_identity']['schema_version'], '20261101')
                self.assertEqual(output['package']['kubernetes_1_36_5_acceptance'], 'unverified')

    def test_profile_preparation_does_not_require_an_existing_backup(self):
        for environment in ('local', 'aws'):
            request = deepcopy(EXAMPLE)
            fixture = request_fixture(environment)
            for key in ('backup_storage_location', 'snapshot_class', 'source_storage_class', 'restore_storage_class',
                        'endpoint', 'region', 'bucket', 'prefix', 'ca_bundle_ref',
                        'identity_ref', 'identity_mode', 'kms_key_ref'):
                request[key] = fixture[key]
            result, output = self.run_play(request, environment, controls={'velero_review_recovery': False})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(output['recovery_plan_included'])
            self.assertEqual(output['readiness'], 'unverified')
            self.assertNotIn('restore_spec', output)
            self.assertNotIn('backup_spec', output)
            self.assertEqual(output['reviewed_request']['local']['enforced_quota_bytes'], 0)
            self.assertEqual(output['local_quota_maintenance_still_required'], environment == 'local')

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

    def test_placeholder_examples_cannot_prepare(self):
        for environment in ('local', 'aws'):
            result, output = self.run_play(EXAMPLE, environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIsNone(output)

    def test_unsafe_scope_identity_retention_and_consistency_fail(self):
        mutations = [
            ('selected_namespaces', ['*']), ('selected_namespaces', ['someone-else']),
            ('selected_namespaces', ['tenant-421', 'tenant-421']),
            ('selected_namespaces', []), ('restore_target_namespace', 'tenant-421'),
            ('compatibility_evidence_ref', ''), ('authorization_review_ref', 'TODO'),
            ('database_recovery_plan_ref', ''), ('app_image_digest', 'latest'),
            ('app_git_commit', 'main'), ('database_version', 'placeholder'),
            ('ca_bundle_ref', ''), ('endpoint', 'http://backup.internal'),
            ('endpoint', 'https://user:password@backup.internal'), ('identity_mode', 'tenant-key'),
            ('rollback_window_hours', 45), ('rpo_hours', 0), ('rpo_hours', True),
            ('schedule_cron', ''), ('backup_hooks', []), ('restore_hooks', []),
            ('flux_suspend_plan_ref', ''), ('restore_capacity_review_ref', ''),
            ('last_known_good_protection_ref', ''), ('retention_cleanup_review_ref', ''),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                request = request_fixture(); request[field] = value
                result, output = self.run_play(request)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIsNone(output)
        for namespace in ('kube-system', 'velero', 'bigbang'):
            request = request_fixture()
            request['approved_namespaces'] = request['selected_namespaces'] = [namespace]
            result, _ = self.run_play(request)
            self.assertNotEqual(result.returncode, 0)

    def test_noquota_and_free_space_are_not_a_backup_budget(self):
        profile = yaml.safe_load((PACKAGE / 'profiles/local.yaml').read_text())['profile']
        self.assertFalse(profile['observed_project_quota_enabled'])
        self.assertFalse(profile['independent_failure_domain'])
        self.assertEqual(profile['backing'], 'quota-bounded-directory-static-local-pv')
        for field, value in (('enforced_quota_bytes', 0), ('quota_maintenance_review_ref', ''),
                             ('reconciled_backup_budget_bytes', 1000),
                             ('snapshot_restore_headroom_bytes', 0),
                             ('longhorn_reserve_review_ref', 'unconfigured'),
                             ('enforced_quota_bytes', True)):
            with self.subTest(field=field):
                request = request_fixture(); request['local'][field] = value
                result, output = self.run_play(request)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(output)

    def test_aws_missing_identity_kms_and_mapping_refuse(self):
        for field in ('kms_key_ref', 'identity_ref', 'region'):
            request = request_fixture('aws'); request[field] = ''
            result, output = self.run_play(request, 'aws')
            self.assertNotEqual(result.returncode, 0)
            self.assertIsNone(output)
        request = request_fixture('aws'); request['aws']['storage_snapshot_mapping_ref'] = ''
        result, _ = self.run_play(request, 'aws')
        self.assertNotEqual(result.returncode, 0)

    def test_hook_failures_unknown_credentials_and_shared_db_guard(self):
        requests = []
        request = request_fixture(); request['restore_hooks'][0]['includedNamespaces'] = ['tenant-421']; requests.append(request)
        request = request_fixture(); request['backup_hooks'][0]['post'] = []; requests.append(request)
        request = request_fixture(); request['backup_hooks'][0]['pre'][0]['exec']['onError'] = 'Continue'; requests.append(request)
        request = request_fixture(); request['restore_hooks'][0]['postHooks'][0]['exec']['onError'] = 'Continue'; requests.append(request)
        request = request_fixture(); request['secret_access_key'] = 'synthetic-forbidden-value'; requests.append(request)
        request = request_fixture(); request['database_scope'] = 'shared'; request['database_recovery_plan_ref'] = ''; requests.append(request)
        for request in requests:
            result, output = self.run_play(request)
            self.assertNotEqual(result.returncode, 0)
            self.assertIsNone(output)

    def test_current_roots_never_select_velero_and_implementation_has_no_api_module(self):
        roots = sorted(p for p in (ROOT / 'clusters').glob('*/kustomization.yaml') if p.parent.name != 'local-velero')
        self.assertGreaterEqual(len(roots), 18) # New unrelated opt-in roots must also stay Velero-free.
        for root in roots:
            rendered = subprocess.check_output(['kubectl', 'kustomize', str(root.parent)], text=True)
            objects = list(yaml.safe_load_all(rendered))
            for obj in objects:
                self.assertNotEqual(obj.get('metadata', {}).get('name'), 'values-velero')
                if obj['kind'] == 'ConfigMap':
                    for text in obj.get('data', {}).values():
                        data = yaml.safe_load(text)
                        if isinstance(data, dict):
                            self.assertFalse(data.get('addons', {}).get('velero', {}).get('enabled', False))
        allowed = {'assert', 'include_vars', 'include_tasks', 'stat', 'template', 'command'}
        for source in [PACKAGE / 'prepare.yaml', *sorted((PACKAGE / 'tasks').glob('*.yaml'))]:
            for line in source.read_text().splitlines():
                stripped = line.strip()
                if stripped.startswith('ansible.builtin.'):
                    self.assertIn(stripped.split(':')[0].split('.')[-1], allowed)


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
