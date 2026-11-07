"""Pure readiness/preservation fixtures and default-no-contact command tests."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import yaml
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('harbor_stage', ROOT / 'scripts/harbor-stage-audit.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
SHA = 'a' * 40


def obj(kind, name, namespace='harbor', spec=None):
    return {'kind': kind, 'metadata': {'name': name, 'namespace': namespace, 'uid': name + '-uid', 'generation': 1},
            'spec': spec or {}, 'status': {'observedGeneration': 1, 'conditions': [{'type': 'Ready', 'status': 'True'}]}}


def deployment(name, namespace='harbor'):
    result = obj('Deployment', name, namespace, {'replicas': 1})
    result['status'].update(replicas=1, readyReplicas=1, updatedReplicas=1, availableReplicas=1)
    return result


class HarborStage(unittest.TestCase):
    def setUp(self):
        operator = deployment('platform-cnpg', 'cnpg-system')
        operator['spec']['template'] = {'spec': {'serviceAccountName': 'platform-cnpg', 'containers': [
            {'name': 'manager', 'image': 'pinned', 'env': [{'name': 'WATCH_NAMESPACE', 'value': 'gitlab,tenant-home-nextcloud'}]}]}}
        self.baseline = {'operator': operator, 'releases': [obj('HelmRelease', name, 'bigbang') for name in ('bigbang', 'platform-cnpg', 'gitlab')],
                         'claims': [obj('PersistentVolumeClaim', 'existing', 'gitlab', {'volumeName': 'retained'})],
                         'databases': [obj('Cluster', 'gitlab-postgres', 'gitlab')]}
        self.baseline['claims'][0]['status'] = {'phase': 'Bound'}
        # Match the pinned CNPG schema: no top-level observedGeneration.
        self.baseline['databases'][0]['status'].pop('observedGeneration')
        self.baseline.update(source=obj('GitRepository', 'cluster-config', 'flux-system', {'url': 'https://github.com/perkforge/perkforge-platform.git', 'ref': {'tag': 'v0.28.0'}}),
                             root=obj('Kustomization', 'cluster-root', 'flux-system', {'path': './big-bang-bootstrap/clusters/local-metrics-limited-pilot-ui', 'sourceRef': {'kind': 'GitRepository', 'name': 'cluster-config'}, 'serviceAccountName': 'platform-reconciler', 'prune': False}))
        for release in self.baseline['releases']:
            if release['metadata']['name'] == 'bigbang': release['spec'] = {'valuesFrom': [], 'postRenderers': [{'kustomize': {'patches': []}}]}
            if release['metadata']['name'] == 'platform-cnpg':
                proposed = yaml.safe_load((ROOT / 'big-bang-bootstrap/configuration/packages/harbor/data-services/operator-watch-review.yaml').read_text())['spec']
                release['spec'] = json.loads(json.dumps(proposed).replace('gitlab,tenant-home-nextcloud,harbor', 'gitlab,tenant-home-nextcloud'))
        self.before = audit.snapshot(self.baseline)
        self.before['cluster_uid'] = 'cluster-uid'
        self.state = copy.deepcopy(self.baseline)
        self.state['operator']['spec']['template']['spec']['containers'][0]['env'][0]['value'] += ',harbor'
        self.state['releases'][1]['spec'] = json.loads(json.dumps(self.state['releases'][1]['spec']).replace('gitlab,tenant-home-nextcloud', 'gitlab,tenant-home-nextcloud,harbor'))
        self.state.update(source=obj('GitRepository', 'cluster-config', 'flux-system', {'url': 'https://github.com/perkforge/perkforge-platform.git', 'ref': {'tag': 'v0.99.0'}}),
                          root=obj('Kustomization', 'cluster-root', 'flux-system', {'path': './big-bang-bootstrap/clusters/local-harbor-data', 'sourceRef': {'kind': 'GitRepository', 'name': 'cluster-config'}, 'serviceAccountName': 'platform-reconciler', 'prune': False}),
                          namespace=obj('Namespace', 'harbor', '', {}), deployments=[deployment('harbor-valkey')], pods=[])
        self.state['source']['status']['artifact'] = {'revision': 'v0.99.0@sha1:' + SHA}
        self.state['root']['status']['lastAppliedRevision'] = 'v0.99.0@sha1:' + SHA
        self.state['namespace']['metadata']['labels'] = {'perkforge.io/owner': 'harbor-foundation-v1'}
        self.state['namespace']['status'] = {'phase': 'Active'}
        self.state['releases'].append(obj('HelmRelease', 'harbor-valkey', 'bigbang'))
        database = obj('Cluster', 'harbor-postgres', spec={'instances': 1})
        database['status']['readyInstances'] = 1
        self.state['databases'].append(database)
        for name in ('postgres', 'valkey'):
            claim = obj('PersistentVolumeClaim', name); claim['status'] = {'phase': 'Bound'}
            self.state['claims'].append(claim)
            pod = obj('Pod', name); pod['status']['phase'] = 'Running'; self.state['pods'].append(pod)

    def verify(self, mode='data'):
        return audit.verify(self.state, self.before, mode, SHA, 'v0.99.0', 'harbor-uid', getattr(self, 'checkpoint', None))

    def test_default_contacts_nothing(self):
        with mock.patch.object(audit.subprocess, 'run') as run, mock.patch.object(Path, 'read_text') as read:
            self.assertEqual(audit.main([]), 0)
            run.assert_not_called(); read.assert_not_called()

    def test_snapshot_is_hashes_only_and_requires_pre_harbor_healthy_stack(self):
        self.assertNotIn('pinned', json.dumps(self.before))
        self.assertNotIn('volumeName', json.dumps(self.before))
        self.assertEqual(self.before['operator']['uid'], 'platform-cnpg-uid')
        for group, changed in [('releases', obj('HelmRelease', 'harbor', 'bigbang')), ('claims', obj('PersistentVolumeClaim', 'harbor-data'))]:
            state = copy.deepcopy(self.baseline); state[group].append(changed)
            with self.assertRaises(audit.Refusal): audit.snapshot(state)
        self.baseline['releases'][0]['status']['conditions'][0]['status'] = 'False'
        with self.assertRaises(audit.Refusal): audit.snapshot(self.baseline)

    def test_exact_data_stage_preserves_existing_state(self):
        result = self.verify()
        self.assertTrue(result['readiness_only'])
        self.assertFalse(result['tls_login_push_pull_restore_accepted'])
        self.assertEqual(result['preserved_releases'], 3)

    def test_recreated_mutated_or_missing_existing_resources_are_refused(self):
        for group, mutation in [('releases', lambda x: x['metadata'].update(uid='replacement')),
                                ('claims', lambda x: x['spec'].update(volumeName='other')),
                                ('databases', lambda x: x['spec'].update(instances=2))]:
            original = copy.deepcopy(self.state[group]); mutation(self.state[group][-1 if group == 'releases' else 0])
            # Ensure release test changes an existing, not new Harbor release.
            if group == 'releases': self.state[group][0]['metadata']['uid'] = 'replacement'
            with self.assertRaises(audit.Refusal): self.verify()
            self.state[group] = original
        self.state['claims'].pop(0)
        with self.assertRaises(audit.Refusal): self.verify()

    def test_operator_changes_beyond_exact_additive_watch_are_refused(self):
        original = copy.deepcopy(self.state['operator'])
        for mutation in [lambda o:o['metadata'].update(uid='new'), lambda o:o['spec']['template']['spec'].update(serviceAccountName='other'),
                         lambda o:o['spec']['template']['spec']['containers'][0].update(image='other'),
                         lambda o:o['spec']['template']['spec']['containers'][0]['env'][0].update(value='harbor')]:
            self.state['operator'] = copy.deepcopy(original); mutation(self.state['operator'])
            with self.assertRaises(audit.Refusal): self.verify()

    def test_source_target_readiness_and_stage_drift_refused(self):
        original = copy.deepcopy(self.state)
        changes = [lambda s:s['source']['spec']['ref'].update(branch='main'), lambda s:s['source']['status']['artifact'].update(revision='v0.98.0@sha1:' + SHA),
                   lambda s:s['root']['spec'].update(prune=True), lambda s:s['root']['metadata'].update(uid='recreated'),
                   lambda s:s['source']['spec'].update(secretRef={'name': 'different'}), lambda s:s['root']['status'].update(observedGeneration=0),
                   lambda s:s['namespace']['metadata'].update(uid='new'), lambda s:s['namespace']['metadata'].update(deletionTimestamp='now'),
                   lambda s:s['releases'].append(obj('HelmRelease', 'harbor', 'bigbang')),
                   lambda s:s['deployments'][0]['status'].update(updatedReplicas=0), lambda s:s['pods'][0]['status'].update(phase='Pending'),
                   lambda s:s['databases'][-1]['status'].update(readyInstances=0), lambda s:s['claims'][-1]['status'].update(phase='Lost')]
        for change in changes:
            with self.subTest(change=change):
                self.state = copy.deepcopy(original); change(self.state)
                with self.assertRaises(audit.Refusal): self.verify()

    def app(self):
        self.checkpoint = audit.data_checkpoint(self.state, self.before, SHA, 'v0.99.0', 'harbor-uid')
        umbrella = self.state['releases'][0]['spec']
        umbrella['valuesFrom'] += [{'kind': 'ConfigMap', 'name': 'values-harbor-' + name, 'valuesKey': 'values.yaml'} for name in ('candidate', 'data', 'application')]
        umbrella['postRenderers'][0]['kustomize']['patches'].append({'target': {'kind': 'Namespace', 'name': 'harbor'}, 'patch': yaml.safe_dump({'$patch': 'delete', 'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': 'harbor'}})})
        self.state['root']['spec']['path'] = './big-bang-bootstrap/clusters/local-harbor-app'
        self.state['releases'].append(obj('HelmRelease', 'harbor', 'bigbang'))
        for name in ('core', 'jobservice', 'registry', 'portal'):
            self.state['deployments'].append(deployment('harbor-' + name))
            pod = obj('Pod', name); pod['status']['phase'] = 'Running'; self.state['pods'].append(pod)
        for name in ('registry', 'joblogs'):
            claim = obj('PersistentVolumeClaim', name); claim['status'] = {'phase': 'Bound'}; self.state['claims'].append(claim)
        self.state.update(services=[], transports=[], transport_crd={'spec': {'versions': [{'name': 'v1alpha1', 'served': True, 'schema': {'openAPIV3Schema': {'properties': {'spec': {'properties': {
            'serverName': {'type': 'string'}, 'insecureSkipVerify': {'type': 'boolean'}, 'rootCAs': {'items': {'properties': {'secret': {'type': 'string'}}}}}}}}}}]}})
        for name in ('core', 'portal'):
            service = obj('Service', 'harbor-' + name, spec={'ports': [{'port': 443, 'targetPort': 8443}]})
            service['metadata']['annotations'] = {'traefik.ingress.kubernetes.io/service.serversscheme': 'https', 'traefik.ingress.kubernetes.io/service.serverstransport': 'harbor-harbor-' + name + '-transport@kubernetescrd'}
            self.state['services'].append(service)
            self.state['transports'].append(obj('ServersTransport', 'harbor-' + name + '-transport', spec={'serverName': 'harbor-' + name, 'insecureSkipVerify': False, 'rootCAs': [{'secret': 'harbor-internal-ca'}]}))
        self.state['services'].append(obj('Service', 'harbor-registry', spec={'ports': [{'port': 5443, 'targetPort': 5443}]}))
        self.state['ingress'] = obj('Ingress', 'harbor-ingress', spec={'ingressClassName': 'traefik', 'tls': [{'hosts': ['harbor.perkforge.home.arpa'], 'secretName': 'harbor-service-tls'}]})
        self.state['ingress']['spec']['rules'] = [{'host': 'harbor.perkforge.home.arpa', 'http': {'paths': [{'path': path, 'pathType': 'Prefix', 'backend': {'service': {'name': 'harbor-portal' if path == '/' else 'harbor-core', 'port': {'number': 443}}}} for path in ('/', '/api/', '/service/', '/v2/', '/c/')]}}]
        self.state['ingress']['metadata']['annotations'] = {'traefik.ingress.kubernetes.io/router.entrypoints': 'websecure', 'traefik.ingress.kubernetes.io/router.tls': 'true'}

    def test_exact_app_is_readiness_not_security_acceptance(self):
        self.app()
        self.assertFalse(self.verify('app')['tls_login_push_pull_restore_accepted'])

    def test_backend_plaintext_wrong_ca_hostname_or_schema_are_refused(self):
        self.app(); original = copy.deepcopy(self.state)
        for change in [lambda s:s['services'][-1]['spec']['ports'][0].update(port=5000),
                       lambda s:s['transports'][0]['spec'].update(insecureSkipVerify=True),
                       lambda s:s['transports'][0]['spec'].update(serverName='other'),
                       lambda s:s['transports'][0]['spec'].update(rootCAs=[{'secret': 'other'}]),
                       lambda s:s['transport_crd']['spec']['versions'][0].update(served=False)]:
            self.state = copy.deepcopy(original); change(self.state)
            with self.assertRaises(audit.Refusal): self.verify('app')

    def test_allowed_helm_changes_do_not_hide_unrelated_release_mutations(self):
        self.app(); original = copy.deepcopy(self.state)
        for change in [lambda s:s['releases'][0]['spec'].update(serviceAccountName='other'),
                       lambda s:s['releases'][1]['spec']['values'].update(image={'tag': 'different'}),
                       lambda s:s['releases'][1]['spec']['postRenderers'][0]['kustomize']['patches'].append({'target': {'kind': 'Deployment', 'name': 'other'}, 'patch': '{}'}),
                       lambda s:s['releases'][0]['spec']['valuesFrom'].append({'kind': 'Secret', 'name': 'other'})]:
            self.state = copy.deepcopy(original); change(self.state)
            with self.assertRaises(audit.Refusal): self.verify('app')

    def test_data_checkpoint_binds_original_database_pvcs_and_release(self):
        self.app(); original = copy.deepcopy(self.state)
        for change in [lambda s:s['databases'][-1]['metadata'].update(uid='replacement'),
                       lambda s:s['claims'][1]['metadata'].update(uid='replacement'),
                       lambda s:s['claims'][1]['spec'].update(volumeName='replacement'),
                       lambda s:s['releases'][-2]['metadata'].update(uid='replacement')]:
            self.state = copy.deepcopy(original); change(self.state)
            with self.assertRaises(audit.Refusal): self.verify('app')
        self.state = original
        for key in ('namespace_uid', 'cluster_uid', 'release', 'commit', 'baseline_sha256'):
            old = self.checkpoint[key]; self.checkpoint[key] = 'wrong'
            with self.assertRaises(audit.Refusal): self.verify('app')
            self.checkpoint[key] = old
        self.checkpoint = None
        with self.assertRaises(audit.Refusal): self.verify('app')

    def test_ingress_route_hostname_and_backend_drift_refused(self):
        self.app(); original = copy.deepcopy(self.state)
        for change in [lambda s:s['ingress']['spec']['rules'][0].update(host='other'),
                       lambda s:s['ingress']['spec']['rules'][0]['http']['paths'][0]['backend']['service'].update(name='other'),
                       lambda s:s['ingress']['spec']['rules'][0]['http']['paths'][0]['backend']['service']['port'].update(number=80),
                       lambda s:s['ingress']['spec']['rules'][0]['http']['paths'].pop(),
                       lambda s:s['ingress']['spec'].update(defaultBackend={'service': {'name': 'other', 'port': {'number': 80}}})]:
            self.state = copy.deepcopy(original); change(self.state)
            with self.assertRaises(audit.Refusal): self.verify('app')

    def test_cli_snapshot_then_stage_uses_only_read_only_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); parent.chmod(0o700)
            config = parent / 'kubeconfig'; config.write_text('synthetic'); config.chmod(0o600)
            evidence = parent / 'before.json'
            state = self.baseline
            calls = []
            def run(command, **kwargs):
                args = command[6:]; calls.append(args)
                if args[:2] == ['config', 'view']: value = json.dumps({'current-context': 'synthetic', 'contexts': [{'name': 'synthetic', 'context': {'cluster': 'synthetic'}}], 'clusters': [{'name': 'synthetic', 'cluster': {'server': 'https://synthetic.invalid:6443', 'certificate-authority-data': 'SYNTHETIC'}}]})
                elif args[:3] == ['get', 'namespace', 'kube-system']: value = 'cluster-uid'
                else:
                    self.assertEqual(args[0], 'get')
                    kinds = {'helmreleases.helm.toolkit.fluxcd.io': 'releases', 'persistentvolumeclaims': 'claims', 'clusters.postgresql.cnpg.io': 'databases', 'deployments': 'deployments', 'pods': 'pods'}
                    if args[1] in kinds: value = {'items': state[kinds[args[1]]]}
                    else: value = state[{'deployment': 'operator', 'gitrepository': 'source', 'kustomization': 'root', 'namespace': 'namespace'}[args[1]]]
                    value = json.dumps(value)
                return mock.Mock(returncode=0, stdout=value)
            params = ['--verify', '--kubeconfig', str(config), '--context', 'synthetic', '--expected-api', 'https://synthetic.invalid:6443', '--expected-cluster-uid', 'cluster-uid', '--baseline', str(evidence)]
            with mock.patch.object(audit.subprocess, 'run', side_effect=run):
                self.assertEqual(audit.main(params + ['--mode', 'snapshot']), 0)
                self.assertEqual(evidence.stat().st_mode & 0o777, 0o600)
                count = len(calls)
                with self.assertRaises(audit.Refusal): audit.main(params + ['--mode', 'snapshot'])
                self.assertEqual(len(calls), count)
                state = self.state
                self.assertEqual(audit.main(params + ['--mode', 'data', '--data-checkpoint', str(parent / 'data.json'), '--expected-namespace-uid', 'harbor-uid', '--release', 'v0.99.0', '--commit', SHA]), 0)
                self.assertTrue(all(args[0] in ('get', 'config') for args in calls))
                self.assertFalse(any('secret' in ' '.join(args).lower() for args in calls))

    def test_cli_wrong_target_and_insecure_file_stop_before_object_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); parent.chmod(0o700)
            config = parent / 'kubeconfig'; config.write_text('synthetic'); config.chmod(0o644)
            params = ['--verify', '--mode', 'snapshot', '--kubeconfig', str(config), '--context', 'synthetic', '--expected-api', 'https://synthetic.invalid:6443', '--expected-cluster-uid', 'cluster-uid', '--baseline', str(parent / 'before.json')]
            with mock.patch.object(audit.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=json.dumps({'current-context': 'synthetic', 'contexts': [{'name': 'synthetic', 'context': {'cluster': 'synthetic'}}], 'clusters': [{'name': 'synthetic', 'cluster': {'server': 'https://wrong.invalid'}}]}))) as run:
                with self.assertRaises(audit.Refusal): audit.main(params)
                run.assert_not_called(); config.chmod(0o600)
                with self.assertRaises(audit.Refusal): audit.main(params)
                self.assertEqual(run.call_count, 1)
                for flags in [{'insecure-skip-tls-verify': True}, {'proxy-url': 'http://other'}, {'tls-server-name': 'other'}, {'certificate-authority-data': ''}]:
                    run.reset_mock()
                    endpoint = {'server': 'https://synthetic.invalid:6443', 'certificate-authority-data': 'SYNTHETIC', **flags}
                    run.return_value.stdout = json.dumps({'current-context': 'synthetic', 'contexts': [{'name': 'synthetic', 'context': {'cluster': 'synthetic'}}], 'clusters': [{'name': 'synthetic', 'cluster': endpoint}]})
                    with self.assertRaises(audit.Refusal): audit.main(params)
                    self.assertEqual(run.call_count, 1)

    def test_protected_evidence_path_refuses_symlinks_hardlinks_and_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); parent.chmod(0o700)
            path = parent / 'evidence'; path.write_text('{}'); path.chmod(0o600)
            self.assertEqual(audit.protected(str(path)), path)
            path.chmod(0o644)
            with self.assertRaises(audit.Refusal): audit.protected(str(path))
            path.chmod(0o600); link = parent / 'link'; link.symlink_to(path)
            with self.assertRaises(audit.Refusal): audit.protected(str(link))
            link.unlink(); os.link(path, link)
            with self.assertRaises(audit.Refusal): audit.protected(str(path))
