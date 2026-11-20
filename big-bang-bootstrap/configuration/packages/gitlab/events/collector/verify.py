#!/usr/bin/env python3
"""Offline integrity verification. Does not fetch, apply, build or publish."""
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent

def verify(root=ROOT):
    m = json.loads((root / 'source.json').read_text())
    assert m['schema_version'] == 1
    assert m['upstream_repository'] == 'https://github.com/mvisonneau/gitlab-ci-pipelines-exporter.git'
    assert m['upstream_commit'] == 'c50ef849a541cd2a826167b9494fa7d0d7d134b4'
    assert m['go_version'] == 'go1.26.8'
    for key in ('prototype_commit', 'patched_tree'):
        assert re.fullmatch('[0-9a-f]{40}', m[key])
    for name, key in [('snapshot.patch', 'patch_sha256'), ('LICENSE.upstream', 'license_sha256')]:
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == m[key]
    assert m['module_files_unchanged'] is True
    assert m['runtime_config_embedded'] is False and m['image_published'] is False
    paths = re.findall(r'^diff --git a/(\S+) b/(\S+)$', (root / 'snapshot.patch').read_text(), re.M)
    allowed = {'docs/pipeline-snapshot-prototype.md', 'internal/cmd/run.go',
               'pkg/config/config.go', 'pkg/config/snapshot.go', 'pkg/config/snapshot_test.go',
               'pkg/controller/controller.go', 'pkg/controller/handlers.go',
               'pkg/snapshot/snapshot.go', 'pkg/snapshot/snapshot_test.go', 'pkg/snapshot/yaml.go'}
    assert paths and {a for a, b in paths} == allowed
    assert all(a == b for a, b in paths)
    return m

if __name__ == '__main__':
    verify()
    print('PASS source patch and upstream license integrity (not build/deployment proof)')
