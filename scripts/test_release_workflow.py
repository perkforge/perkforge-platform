"""Offline release gates and permissions; no GitHub or Kubernetes API calls."""
import json
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

import yaml


class ReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load(Path('.github/workflows/configuration-release.yml').read_text(), Loader=yaml.BaseLoader)
        cls.jobs = cls.workflow['jobs']

    def test_only_main_push_can_write_release(self):
        self.assertEqual(set(self.workflow['on']), {'push', 'pull_request', 'workflow_dispatch'})
        self.assertEqual(self.workflow['on']['push'], {'branches': ['main']})
        self.assertEqual(self.jobs['release']['if'], "github.event_name == 'push' && github.ref == 'refs/heads/main'")
        self.assertEqual(self.jobs['release']['needs'], ['configuration', 'release-checks'])
        self.assertFalse(self.workflow['concurrency']['cancel-in-progress'] == 'true')

    def test_checks_read_only_and_minimal_release_rights(self):
        self.assertEqual(self.workflow['permissions'], {'contents': 'read'})
        for name in ('configuration', 'release-checks'):
            self.assertEqual(self.jobs[name]['permissions'], {'contents': 'read'})
        self.assertEqual(self.jobs['release']['permissions'], {'contents': 'write', 'pull-requests': 'write', 'issues': 'write'})
        step = self.jobs['release']['steps'][0]
        self.assertEqual(step['with']['token'], '${{ secrets.GITHUB_TOKEN }}')
        self.assertRegex(step['uses'], r'^googleapis/release-please-action@[0-9a-f]{40}$')
        for job in self.jobs.values():
            for step in job.get('steps', []):
                if 'uses' in step:
                    self.assertRegex(step['uses'], r'@[0-9a-f]{40}$')

    def test_reuses_configuration_checks_and_records_resolved_tag(self):
        workflow_path = self.jobs['configuration']['uses'].removeprefix('./')
        check = yaml.load(Path(workflow_path).read_text(), Loader=yaml.BaseLoader)
        self.assertIn('workflow_call', check['on'])
        steps = self.jobs['release']['steps']
        record = steps[-1]
        self.assertEqual(record['if'], "steps.release.outputs.release_created == 'true'")
        self.assertEqual(record['env']['RELEASE_TAG'], '${{ steps.release.outputs.tag_name }}')
        self.assertIn('git rev-parse "$RELEASE_TAG^{commit}"', record['run'])
        self.assertIn('test "$resolved" = "$GITHUB_SHA"', record['run'])
        self.assertNotRegex(record['run'], r'git (push|tag)')
        self.assertFalse(any('workflow_run' in str(value) for value in self.workflow['on']))

    def test_version_manifest_and_first_release_inputs(self):
        config = json.loads(Path('release-please-config.json').read_text())
        package = config['packages']['.']
        self.assertRegex(config['bootstrap-sha'], r'^[0-9a-f]{40}$')
        self.assertEqual(package['release-type'], 'simple')
        self.assertEqual(package['version-file'], 'VERSION')
        self.assertEqual(package['initial-version'], '0.1.0')
        self.assertFalse(package['include-component-in-tag'])
        self.assertTrue(package['include-v-in-tag'])
        self.assertFalse(package['bump-minor-pre-major'])
        self.assertFalse(package['bump-patch-for-minor-pre-major'])
        version = Path('VERSION').read_text().strip()
        self.assertRegex(version, r'^\d+\.\d+\.\d+$')
        self.assertEqual(json.loads(Path('.release-please-manifest.json').read_text())['.'], version)


class ReleaseRefTests(unittest.TestCase):
    def verify(self, tag='v1.2.3', expected=None, **overrides):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'gh').write_text(r'''#!/bin/sh
[ "$FAKE_MISSING" != true ] || exit 1
if [ "$1" = release ]; then
  printf 'v1.2.3\t%s\t%s\n' "$FAKE_DRAFT" "$FAKE_PRERELEASE"
else
  printf '%s\n' "$FAKE_COMMIT"
fi
''')
            (folder / 'git').write_text(r'''#!/bin/sh
printf '%s\trefs/tags/v1.2.3\n' "$FAKE_TAG_OBJECT"
[ "$FAKE_ANNOTATED" != true ] || printf '%s\trefs/tags/v1.2.3^{}\n' "$FAKE_COMMIT"
''')
            for tool in ('gh', 'git'):
                (folder / tool).chmod(0o755)
            env = {**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                   'FAKE_DRAFT': 'false', 'FAKE_PRERELEASE': 'false', 'FAKE_COMMIT': 'a' * 40,
                   'FAKE_TAG_OBJECT': 'a' * 40, **overrides}
            args = ['bash', 'scripts/verify-release-ref.sh', 'fixture/config', tag]
            if expected is not None:
                args.append(expected)
            return subprocess.run(args, env=env, text=True, capture_output=True)

    def test_lightweight_and_annotated_tags_resolve(self):
        for overrides in ({}, {'FAKE_ANNOTATED': 'true', 'FAKE_TAG_OBJECT': 'b' * 40}):
            result = self.verify(expected='a' * 40, **overrides)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Resolved source commit: ' + 'a' * 40, result.stdout)

    def test_missing_prerelease_floating_and_non_semver_refs_fail(self):
        for tag, flags in [('v1.2.3', {'FAKE_MISSING': 'true'}),
                           ('v1.2.3', {'FAKE_PRERELEASE': 'true'}),
                           ('v1.2.3', {'FAKE_DRAFT': 'true'}),
                           ('main', {}), ('v1.2', {}), ('v01.2.3', {})]:
            with self.subTest(tag=tag, flags=flags):
                self.assertNotEqual(self.verify(tag, **flags).returncode, 0)

    def test_tag_and_commit_api_must_agree(self):
        result = self.verify(FAKE_TAG_OBJECT='b' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('consistent source commit', result.stderr)

    def test_retargeted_published_tag_is_rejected(self):
        result = self.verify(expected='b' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Tag resolution changed', result.stderr)


if __name__ == '__main__':
    unittest.main()
