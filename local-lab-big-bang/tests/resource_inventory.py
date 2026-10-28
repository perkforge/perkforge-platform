"""Resource accounting for rendered TEST objects, not a configuration generator."""
from collections import Counter
from decimal import Decimal
import math


def quantity(value):
    text = str(value or 0)
    for unit, factor in [('Ki', 1024), ('Mi', 1024**2), ('Gi', 1024**3),
                         ('Ti', 1024**4), ('K', 1000), ('M', 1000**2),
                         ('G', 1000**3), ('m', .001), ('u', .000001), ('n', .000000001)]:
        if text.endswith(unit):
            return float(Decimal(text[:-len(unit)])) * factor
    return float(Decimal(text))


def pod_resource(pod, field, kind):
    regular = sum(quantity(c.get('resources', {}).get(kind, {}).get(field))
                  for c in pod.get('containers', []))
    sidecars = maximum = 0
    for container in pod.get('initContainers', []):
        amount = quantity(container.get('resources', {}).get(kind, {}).get(field))
        if container.get('restartPolicy') == 'Always':
            sidecars += amount
            maximum = max(maximum, sidecars)
        else:
            maximum = max(maximum, amount + sidecars)
    return max(regular + sidecars, maximum) + quantity(pod.get('overhead', {}).get(field))


def inventory(objects):
    result = {'objects': dict(Counter(o['kind'] for o in objects)),
              'workloads': [], 'claims': [], 'images': []}
    for obj in objects:
        kind, spec = obj['kind'], obj.get('spec', {})
        if kind in ('Deployment', 'StatefulSet', 'DaemonSet', 'Job', 'Pod', 'CronJob'):
            pod = spec if kind == 'Pod' else (spec['jobTemplate']['spec']['template']['spec']
                  if kind == 'CronJob' else spec['template']['spec'])
            hook = obj['metadata'].get('annotations', {}).get('helm.sh/hook')
            replicas = spec.get('replicas', spec.get('parallelism', 1))
            item = {'kind': kind, 'name': obj['metadata']['name'], 'replicas': replicas,
                    'hook': hook, 'requests': {}, 'limits': {}, 'unsized': []}
            for resource in ('cpu', 'memory'):
                for mode in ('requests', 'limits'):
                    item[mode][resource] = pod_resource(pod, resource, mode)
            for container in pod.get('containers', []) + pod.get('initContainers', []):
                result['images'].append(container['image'])
                for mode in ('requests', 'limits'):
                    for resource in ('cpu', 'memory'):
                        if not container.get('resources', {}).get(mode, {}).get(resource):
                            item['unsized'].append(container['name'] + ':' + mode + '.' + resource)
            surge = 0
            if kind == 'Deployment' and spec.get('strategy', {}).get('type', 'RollingUpdate') != 'Recreate':
                configured = spec.get('strategy', {}).get('rollingUpdate', {}).get('maxSurge', '25%')
                surge = math.ceil(replicas * float(configured[:-1]) / 100) if str(configured).endswith('%') else int(configured)
            item['maxSurgePods'] = surge
            result['workloads'].append(item)
            for claim in spec.get('volumeClaimTemplates', []):
                result['claims'].append({'name': obj['metadata']['name'] + '/' + claim['metadata']['name'],
                    'bytes': quantity(claim['spec']['resources']['requests']['storage']) * replicas,
                    'class': claim['spec'].get('storageClassName'), 'replicas': replicas})
        elif kind == 'PersistentVolumeClaim':
            result['claims'].append({'name': obj['metadata']['name'],
                'bytes': quantity(spec['resources']['requests']['storage']),
                'class': spec.get('storageClassName'), 'replicas': 1})
    result['images'] = sorted(set(result['images']))
    result['steadyRequestsCPU'] = sum(w['requests']['cpu'] * w['replicas'] for w in result['workloads'] if not w['hook'])
    result['steadyRequestsMi'] = sum(w['requests']['memory'] * w['replicas'] for w in result['workloads'] if not w['hook']) / 1024**2
    result['steadyLimitsCPU'] = sum(w['limits']['cpu'] * w['replicas'] for w in result['workloads'] if not w['hook'])
    result['surgeRequestsCPU'] = sum(w['requests']['cpu'] * w['maxSurgePods'] for w in result['workloads'] if not w['hook'])
    result['surgeRequestsMi'] = sum(w['requests']['memory'] * w['maxSurgePods'] for w in result['workloads'] if not w['hook']) / 1024**2
    result['steadyLimitsMi'] = sum(w['limits']['memory'] * w['replicas'] for w in result['workloads'] if not w['hook']) / 1024**2
    return result
