"""Future Harbor stages: effective pinned Flux post-renders and preservation."""
import copy
import json
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name

ROOT = Path(__file__).resolve().parents[2]


def named(objects, kind, name):
    return next(o for o in objects if o['kind'] == kind and o['metadata']['name'] == name)


def indexed(objects):
    return {(o['kind'], o['metadata'].get('namespace'), o['metadata']['name']): o for o in objects}


def postrender(objects, renderers):
    for renderer in renderers:
        with tempfile.TemporaryDirectory(prefix='harbor-postrender-') as directory:
            path = Path(directory)
            (path / 'objects.yaml').write_text(yaml.safe_dump_all(objects))
            (path / 'kustomization.yaml').write_text(yaml.safe_dump({'resources': ['objects.yaml'], **renderer['kustomize']}))
            objects = build(path)
    return objects


class HarborActivation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.baseline = build(ROOT / 'clusters/local-metrics-limited-pilot-ui')
        cls.data = build(ROOT / 'clusters/local-harbor-data')
        cls.app = build(ROOT / 'clusters/local-harbor-app')
        cls.parent = named(cls.app, 'HelmRelease', 'bigbang')
        cls.outer_raw = helm(cls.sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(cls.app, cls.parent))
        cls.outer = postrender(cls.outer_raw, cls.parent['spec']['postRenderers'])
        cls.release = named(cls.outer, 'HelmRelease', 'harbor')
        cls.raw = helm(cls.sources / 'harbor/chart', release_name(cls.release), 'harbor', child_values(cls.outer, 'harbor'))
        cls.final = postrender(cls.raw, cls.release['spec']['postRenderers'])

    def test_data_root_only_adds_data_and_extends_existing_watch(self):
        before, after = indexed(self.baseline), indexed(self.data)
        operator_key = ('HelmRelease', 'bigbang', 'platform-cnpg')
        for key, obj in before.items():
            if key != operator_key:
                self.assertEqual(after[key], obj, key)
        expected = copy.deepcopy(before[operator_key])
        proposal = yaml.safe_load((ROOT / 'configuration/packages/harbor/data-services/operator-watch-review.yaml').read_text())
        expected['spec'].update(proposal['spec'])
        self.assertEqual(after[operator_key], expected)
        self.assertFalse(any(o['metadata']['name'] in ('values-harbor-candidate', 'values-harbor-application') for o in self.data))
        self.assertFalse(named(self.data, 'HelmRelease', 'harbor-valkey')['spec']['suspend'])
        self.assertEqual(named(self.data, 'Cluster', 'harbor-postgres')['spec']['instances'], 1)

    def test_app_root_preserves_all_existing_objects_except_umbrella_additions(self):
        before, after = indexed(self.data), indexed(self.app)
        for key, obj in before.items():
            if key != ('HelmRelease', 'bigbang', 'bigbang'):
                self.assertEqual(after[key], obj, key)
        original = before[('HelmRelease', 'bigbang', 'bigbang')]
        changed = copy.deepcopy(self.parent)
        self.assertEqual([x['name'] for x in changed['spec']['valuesFrom'][-3:]],
                         ['values-harbor-candidate', 'values-harbor-data', 'values-harbor-application'])
        del changed['spec']['valuesFrom'][-3:]
        deletion = changed['spec']['postRenderers'][0]['kustomize']['patches'].pop()
        self.assertEqual(deletion['target'], {'kind': 'Namespace', 'name': 'harbor'})
        self.assertEqual(changed, original)
        baseline_outer = helm(self.sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(self.baseline, named(self.baseline, 'HelmRelease', 'bigbang')))
        baseline_outer = postrender(baseline_outer, named(self.baseline, 'HelmRelease', 'bigbang')['spec']['postRenderers'])
        old, new = indexed(baseline_outer), indexed(self.outer)
        for key, obj in old.items():
            self.assertEqual(new[key], obj, key)

    def test_audit_fingerprints_allow_only_effective_reviewed_release_deltas(self):
        spec = importlib.util.spec_from_file_location('harbor_audit_render_contract', ROOT.parent / 'scripts/harbor-stage-audit.py')
        audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
        for name in ('bigbang', 'platform-cnpg'):
            original = audit.release_fingerprint(named(self.baseline, 'HelmRelease', name))
            self.assertEqual(audit.release_fingerprint(named(self.data, 'HelmRelease', name), stage='data'), original)
            self.assertEqual(audit.release_fingerprint(named(self.app, 'HelmRelease', name), stage='app'), original)

    def test_operator_config_checksums_match_pinned_chart_and_only_reviewed_watch_delta(self):
        spec = importlib.util.spec_from_file_location('harbor_audit_operator_contract', ROOT.parent / 'scripts/harbor-stage-audit.py')
        audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
        chart = yaml.safe_load((self.sources / 'cnpg/Chart.yaml').read_text())
        self.assertEqual(chart['version'], '0.29.1')
        deployments = []
        for objects in (self.baseline, self.data, self.app):
            release = named(objects, 'HelmRelease', 'platform-cnpg')
            values = ordered_values(objects, release) + [yaml.safe_dump(release['spec'].get('values', {}))]
            rendered = helm(self.sources / 'cnpg', 'platform-cnpg', 'cnpg-system', values)
            effective = postrender(rendered, release['spec']['postRenderers'])
            deployment = named(effective, 'Deployment', 'platform-cnpg')
            watched = next(e['value'] for c in deployment['spec']['template']['spec']['containers']
                           if c['name'] == 'manager' for e in c['env'] if e['name'] == 'WATCH_NAMESPACE')
            self.assertEqual(deployment['spec']['template']['metadata']['annotations']['checksum/config'],
                             audit.OPERATOR_CONFIG_CHECKSUMS[watched])
            deployment['metadata'].update(uid='synthetic-operator', generation=1)
            deployment['status'] = dict(observedGeneration=1, replicas=1, updatedReplicas=1, readyReplicas=1, availableReplicas=1)
            deployments.append(deployment)
        for changed in deployments[1:]:
            self.assertEqual(audit.operator_identity(deployments[0])[0], audit.operator_identity(changed)[0])
            normalized = copy.deepcopy(changed['spec'])
            normalized['template']['metadata']['annotations']['checksum/config'] = deployments[0]['spec']['template']['metadata']['annotations']['checksum/config']
            for container in normalized['template']['spec']['containers']:
                for entry in container.get('env', []):
                    if entry['name'] == 'WATCH_NAMESPACE':
                        entry['value'] = 'gitlab,tenant-home-nextcloud'
            self.assertEqual(normalized, deployments[0]['spec'])

    def test_effective_app_keeps_namespace_ownership_scanner_and_exporter_off(self):
        self.assertFalse(any(o['kind'] == 'Namespace' and o['metadata']['name'] == 'harbor' for o in self.outer))
        self.assertTrue(any(o['kind'] == 'Namespace' and o['metadata']['name'] == 'harbor' for o in self.outer_raw))
        spec = self.release['spec']
        self.assertFalse(spec['suspend'])
        self.assertEqual(spec['serviceAccountName'], 'harbor-installer')
        self.assertEqual(spec['storageNamespace'], 'harbor')
        self.assertIn({'name': 'harbor-valkey', 'namespace': 'bigbang'}, spec['dependsOn'])
        for stage in ('install', 'upgrade'):
            self.assertFalse(spec[stage]['remediation']['remediateLastFailure'])
            self.assertEqual(spec[stage]['remediation']['retries'], 0)
        names = {o['metadata']['name'] for o in self.final}
        self.assertFalse(names & {'harbor-nginx', 'harbor-exporter', 'harbor-trivy', 'harbor-database', 'harbor-redis'})
        self.assertFalse(any(o['kind'] in ('ServiceMonitor', 'ClusterRole', 'Role', 'ClusterRoleBinding', 'RoleBinding') for o in self.final))
        self.assertFalse(any(o.get('data') or o.get('stringData') for o in self.final if o['kind'] == 'Secret'))

    def test_https_routes_verify_each_backend_name_and_ca(self):
        ingress = named(self.final, 'Ingress', 'harbor-ingress')
        self.assertEqual(ingress['spec']['ingressClassName'], 'traefik')
        self.assertEqual(ingress['spec']['tls'], [{'secretName': 'harbor-service-tls', 'hosts': ['harbor.perkforge.home.arpa']}])
        self.assertEqual(ingress['metadata']['annotations']['traefik.ingress.kubernetes.io/router.entrypoints'], 'websecure')
        rule = ingress['spec']['rules'][0]
        self.assertEqual(rule['host'], 'harbor.perkforge.home.arpa')
        self.assertTrue(all(entry['pathType'] == 'Prefix' for entry in rule['http']['paths']))
        paths = {entry['path']: entry['backend']['service'] for entry in rule['http']['paths']}
        self.assertEqual(set(paths), {'/', '/api/', '/service/', '/v2/', '/c/'})
        for path, service in paths.items():
            self.assertEqual(service, {'name': 'harbor-portal' if path == '/' else 'harbor-core', 'port': {'number': 443}})
        for component in ('core', 'portal'):
            service = named(self.final, 'Service', 'harbor-' + component)
            annotations = service['metadata']['annotations']
            self.assertEqual(annotations['traefik.ingress.kubernetes.io/service.serversscheme'], 'https')
            self.assertEqual(annotations['traefik.ingress.kubernetes.io/service.serverstransport'], f'harbor-harbor-{component}-transport@kubernetescrd')
            transport = named(self.app, 'ServersTransport', f'harbor-{component}-transport')
            self.assertEqual(transport['spec'], {'serverName': 'harbor-' + component, 'insecureSkipVerify': False, 'rootCAs': [{'secret': 'harbor-internal-ca'}]})
            self.assertEqual(service['spec']['ports'][0]['targetPort'], 8443)

    def test_registry_tls_patch_repairs_the_actual_inherited_port_mismatch(self):
        inherited = postrender(self.raw, self.release['spec']['postRenderers'][:-1])
        old = named(inherited, 'Service', 'harbor-registry')
        fixed = named(self.final, 'Service', 'harbor-registry')
        self.assertEqual(old['spec']['ports'][0]['port'], 5000)
        self.assertEqual(fixed['spec']['ports'][0], {'name': 'https-registry', 'port': 5443, 'targetPort': 5443})
        expected = copy.deepcopy(inherited)
        named(expected, 'Service', 'harbor-registry')['spec']['ports'][0] = fixed['spec']['ports'][0]
        self.assertEqual(indexed(expected), indexed(self.final))
        core = named(self.final, 'ConfigMap', 'harbor-core')['data']
        self.assertEqual(core['REGISTRY_URL'], 'https://harbor-registry:5443')
        self.assertEqual(core['REGISTRY_CONTROLLER_URL'], 'https://harbor-registry:8443')

    def test_all_pods_use_registry_secret_no_tokens_and_tls_secret_references(self):
        consumers = []
        for obj in self.final:
            if obj['kind'] != 'Deployment': continue
            pod = obj['spec']['template']['spec']; consumers.append(obj)
            self.assertEqual(pod['imagePullSecrets'], [{'name': 'private-registry'}])
            self.assertFalse(pod['automountServiceAccountToken'])
            self.assertEqual(obj['spec']['replicas'], 1)
            names = {v['secret']['secretName'] for v in pod.get('volumes', []) if 'secret' in v}
            component = obj['metadata']['name'].replace('harbor-', '')
            self.assertIn('harbor-' + component + '-tls', names)
            self.assertTrue(all('@sha256:' in c['image'] or c['image'].startswith('registry1.dso.mil/') for c in pod['containers']))
        self.assertEqual(len(consumers), 4)
        self.assertEqual(sum(len(o['spec']['template']['spec']['containers']) for o in consumers), 5)
        for name in ('harbor-jobservice', 'harbor-registry'):
            obj = named(self.final, 'Deployment', name)
            self.assertEqual(obj['spec']['strategy']['type'], 'Recreate')
            self.assertEqual(obj['spec']['template']['spec']['nodeSelector'], {'storage.perkforge.io/worker': 'true'})

    def test_installer_authorizes_exact_native_crud_without_new_global_authority(self):
        foundation = build(ROOT / 'configuration/packages/harbor/prerequisites')
        rules = named(foundation, 'Role', 'harbor-installer')['rules']
        mapping = {'Secret': ('', 'secrets'), 'ConfigMap': ('', 'configmaps'), 'Service': ('', 'services'),
                   'PersistentVolumeClaim': ('', 'persistentvolumeclaims'), 'Deployment': ('apps', 'deployments'),
                   'Ingress': ('networking.k8s.io', 'ingresses')}
        for obj in self.final:
            group, resource = mapping[obj['kind']]
            for verb in ('get', 'list', 'watch', 'create', 'update', 'patch', 'delete'):
                self.assertTrue(any(group in r['apiGroups'] and resource in r['resources'] and verb in r['verbs'] for r in rules), (obj['kind'], verb))
        transport = named(foundation, 'Role', 'harbor-application-gitops')
        self.assertEqual(transport['metadata']['namespace'], 'harbor')
        self.assertEqual(transport['rules'], [{'apiGroups': ['traefik.io'], 'resources': ['serverstransports'], 'verbs': ['get', 'list', 'watch', 'create', 'update', 'patch']}])
        self.assertFalse(any(o['kind'] in ('ClusterRole', 'ClusterRoleBinding') for o in foundation))
