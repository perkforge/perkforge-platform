"""Independent mutation cases against Helm-rendered tenant commit ecafe09 (test digest only)."""
import copy
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT/'local-lab/scripts'))
spec = importlib.util.spec_from_file_location('portal_identity', ROOT/'local-lab/scripts/portal_application.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def cases():
    c = module.load_contract()
    baseline = copy.deepcopy(c)
    c['imageDigest'] = 'sha256:' + 'a'*64  # synthetic; never written to the desired contract
    policies = {o['metadata']['name']: o for o in module.admission(c) if o['kind']=='ValidatingAdmissionPolicy'}
    objects = json.loads((ROOT/'local-lab/tests/fixtures/portal/workload.json').read_text())
    deployment = next(o for o in objects if o['kind']=='Deployment')
    service = next(o for o in objects if o['kind']=='Service')
    request = {'namespace': c['namespace'], 'kind': {'group':'apps','version':'v1','kind':'Deployment'},
               'resource': {'group':'apps','version':'v1','resource':'deployments'}, 'subResource':'',
               'operation':'CREATE', 'userInfo': {'username': f'system:serviceaccount:{c["fleetAgentNamespace"]}:{c["deployerServiceAccount"]}', 'groups': []}}
    result=[]
    def add(name, obj, allowed, policy='portal-template-contract', req=None):
        result.append({'name':name,'object':obj,'request':req or request,
                       'expressions':[v['expression'] for v in policies[policy]['spec']['validations']], 'allowed':allowed})
    add('approved-rendered-deployment', deployment, True)
    chart = os.environ.get('PORTAL_CHART_DIR')
    if chart:
        def render(*overrides):
            output = subprocess.check_output([os.environ.get('HELM','helm'), 'template', 'home-portal', chart,
                '--namespace', c['namespace'], '--kube-version', '1.36.5',
                '-f', str(module.PREVIEW/'helm-values.yaml'),
                '--set', 'enabled=true', '--set', 'image.digest='+c['imageDigest'], *overrides], text=True)
            return list(yaml.safe_load_all(output))
        rendered=render()
        if rendered != objects:
            raise ValueError('Pinned tenant chart output drifted from the reviewed admission fixture')
        for key,value in [('identity.issuer','https://attacker.invalid/realms/perkforge'),
                          ('identity.clientId','attacker'),('identity.audience','attacker-api'),
                          ('identity.existingSecret','privileged-secret'),
                          ('portalOrigin','https://attacker.invalid')]:
            modified=next(o for o in render('--set',key+'='+value) if o['kind']=='Deployment')
            add('real-chart-override-'+key,modified,False)

    pod = {'apiVersion':'v1','kind':'Pod','metadata':{'name':'home-portal-fixture','namespace':c['namespace']}, 'spec':copy.deepcopy(deployment['spec']['template']['spec'])}
    add('approved-controller-pod', pod, True,'portal-pod-contract')
    replica = copy.deepcopy(deployment); replica['kind']='ReplicaSet';replica['metadata']['name']='home-portal-fixture';replica['spec'].pop('strategy')
    replica_request=copy.deepcopy(request);replica_request['kind']['kind']='ReplicaSet'
    add('approved-controller-replicaset',replica,True,req=replica_request)
    def mutate(name, change):
        obj=copy.deepcopy(deployment);p=obj['spec']['template']['spec'];container=p['containers'][0]
        change(obj,p,container)
        add(name,obj,False)
        pod_obj=copy.deepcopy(pod);pod_obj['spec']=p
        add(name+'-pod',pod_obj,False,'portal-pod-contract')
    for field in ('OIDC_ISSUER','OIDC_CLIENT_ID','OIDC_AUDIENCE','PORTAL_ORIGIN','TENANT_SOURCE'):
        def override(_o,_p,container,field=field):
            next(e for e in container['env'] if e['name']==field)['value']='https://attacker.invalid'
        mutate('override-'+field,override)
    def replace_env(_o,_p,container):
        e=next(e for e in container['env'] if e['name']=='OIDC_ISSUER');e.pop('value');e['valueFrom']={'configMapKeyRef':{'name':'attacker','key':'issuer'}}
    mutate('valueFrom-injection',replace_env)
    mutate('extra-node-options',lambda o,p,v:v['env'].append({'name':'NODE_OPTIONS','value':'--require=/tmp/evil.js'}))
    mutate('duplicate-env',lambda o,p,v:v['env'].append(copy.deepcopy(v['env'][0])))
    mutate('envFrom-secret',lambda o,p,v:v.update(envFrom=[{'secretRef':{'name':'privileged-secret'}}]))
    def secret(_o,_p,v):next(e for e in v['env'] if e['name']=='OIDC_CLIENT_SECRET')['valueFrom']['secretKeyRef']['name']='admin-secret'
    mutate('unapproved-secret-reference',secret)
    mutate('wrong-service-account',lambda o,p,v:p.update(serviceAccountName='admin'))
    mutate('token-automount',lambda o,p,v:p.update(automountServiceAccountToken=True))
    mutate('secret-volume',lambda o,p,v:p.update(volumes=[{'name':'secret','secret':{'secretName':'admin-secret'}}]))
    mutate('hostPath',lambda o,p,v:p.update(volumes=[{'name':'host','hostPath':{'path':'/'}}]))
    mutate('projected-api-token',lambda o,p,v:p.update(volumes=[{'name':'token','projected':{'sources':[{'serviceAccountToken':{'path':'token'}}]}}]))
    mutate('sidecar',lambda o,p,v:p['containers'].append(copy.deepcopy(v)))
    mutate('init-container',lambda o,p,v:p.update(initContainers=[{'name':'evil','image':v['image']}]))
    mutate('ephemeral-container',lambda o,p,v:p.update(ephemeralContainers=[{'name':'evil','image':v['image']}]))
    mutate('unapproved-image',lambda o,p,v:v.update(image='attacker/image:latest'))
    mutate('command-override',lambda o,p,v:v.update(command=['sh','-c','env']))
    mutate('args-override',lambda o,p,v:v.update(args=['evil.js']))
    mutate('lifecycle-exec',lambda o,p,v:v.update(lifecycle={'postStart':{'exec':{'command':['sh']}}}))
    mutate('exec-probe',lambda o,p,v:v.update(livenessProbe={'exec':{'command':['sh']}}))
    mutate('external-probe',lambda o,p,v:v['livenessProbe']['httpGet'].update(host='attacker.invalid'))
    mutate('privileged',lambda o,p,v:v['securityContext'].update(privileged=True))
    mutate('root-container',lambda o,p,v:v['securityContext'].update(runAsUser=0))
    mutate('host-network',lambda o,p,v:p.update(hostNetwork=True))
    mutate('host-pid',lambda o,p,v:p.update(hostPID=True))
    mutate('host-port',lambda o,p,v:v['ports'][0].update(hostPort=3000))
    mutate('custom-dns',lambda o,p,v:p.update(dnsPolicy='None',dnsConfig={'nameservers':['1.2.3.4']}))
    mutate('host-alias',lambda o,p,v:p.update(hostAliases=[{'ip':'1.2.3.4','hostnames':['keycloak.local-lab.test']}]))
    mutate('unmasked-proc',lambda o,p,v:v['securityContext'].update(procMount='Unmasked'))
    mutate('unconfined-apparmor',lambda o,p,v:v['securityContext'].update(appArmorProfile={'type':'Unconfined'}))
    mutate('unsafe-sysctl',lambda o,p,v:p['securityContext'].update(sysctls=[{'name':'kernel.shm_rmid_forced','value':'0'}]))
    mutate('interactive-tty',lambda o,p,v:v.update(tty=True))
    add('approved-clusterip-service', service, True,'portal-service-contract')
    for field,value in [('type','NodePort'),('externalIPs',['1.2.3.4']),('externalName','attacker.invalid')]:
        obj=copy.deepcopy(service);obj['spec'][field]=value;add('service-'+field,obj,False,'portal-service-contract')
    for resource,group,subresource,allowed in [('deployments','apps','',True),('services','','',True),('secrets','','',False),('configmaps','','',False),('roles','rbac.authorization.k8s.io','',False),('networkpolicies','networking.k8s.io','',False),('pods','','exec',False),('deployments','apps','scale',False),('serviceaccounts','','token',False)]:
        req=copy.deepcopy(request);req['resource']={'group':group,'version':'v1','resource':resource};req['subResource']=subresource
        add('deployer-'+resource+'-'+subresource,{},allowed,'portal-deployer-surface',req)
    # Evaluate the exact matchConditions as well, not a Python substitute for CEL.
    for policy in policies.values():
        for condition in policy['spec']['matchConditions']:
            result.append({'name':policy['metadata']['name']+'-match-'+condition['name'],'object':deployment,'request':request,'expressions':[condition['expression']],'allowed':True})
    other=copy.deepcopy(request);other['namespace']='tenant-home-nextcloud'
    add('deployer-cannot-write-other-namespace',{},False,'portal-deployer-surface',other)
    result.append({'name':'other-namespace-not-selected','object':deployment,'request':other,'expressions':[policies['portal-template-contract']['spec']['matchConditions'][0]['expression']],'allowed':False})
    baseline_policy=next(o for o in module.admission(baseline) if o['kind']=='ValidatingAdmissionPolicy')
    result.append({'name':'unapproved-image-contract-denies-even-fixture','object':deployment,'request':request,'expressions':[v['expression'] for v in baseline_policy['spec']['validations']],'allowed':False})
    return result

if __name__=='__main__':
    print(json.dumps(cases()))
