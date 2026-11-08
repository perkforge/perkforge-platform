#!/usr/bin/env python3
"""Offline API-shaped fixture. No network, storage backend, snapshot or real bytes."""
import json
import os
from pathlib import Path
import sys

state_path=Path(os.environ['VELERO_FAKE_STATE'])
state=json.loads(state_path.read_text())
args=sys.argv[1:]
while args and args[0].startswith('--'):
    option=args.pop(0)
    if '=' not in option:args.pop(0)
with Path(str(state_path)+'.calls').open('a') as log:log.write(json.dumps(args)+'\n')
ns=args[args.index('-n')+1] if '-n' in args else ''
kindmap={'configmap':'ConfigMap','namespace':'Namespace','pod':'Pod','pvc':'PersistentVolumeClaim','backup':'Backup','restore':'Restore','schedule':'Schedule','gitrepository':'GitRepository','kustomization':'Kustomization','helmrelease':'HelmRelease','kustomizations.kustomize.toolkit.fluxcd.io':'Kustomization'}
def key(kind,name,namespace=''):return '|'.join((kind,namespace,name))
def output(value):
    state_path.write_text(json.dumps(state))
    print(json.dumps(value) if not isinstance(value,str) else value)
    raise SystemExit(0)
def insert(obj):
    meta=obj['metadata'];meta.setdefault('uid','uid-'+meta.get('namespace','')+'-'+meta['name']);meta.setdefault('resourceVersion','1')
    if obj['kind']=='PersistentVolumeClaim':
        obj['spec'].setdefault('volumeName','pv-'+meta['namespace']+'-'+meta['name']);obj['status']={'phase':'Bound'}
    state[key(obj['kind'],meta['name'],meta.get('namespace',''))]=obj
    if obj['kind'] in ('Backup','Restore'):
        obj['status']={'phase':'Completed','errors':0,'warnings':0}
    if obj['kind']=='Restore':
        b=state[key('Backup',obj['spec']['backupName'],'velero')]
        for source,target in obj['spec']['namespaceMapping'].items():
            for resource in list(state.values()):
                if isinstance(resource,dict) and resource.get('kind') in ('Pod','PersistentVolumeClaim') and resource.get('metadata',{}).get('namespace')==source:
                    copied=json.loads(json.dumps(resource));copied['metadata']['namespace']=target;copied['metadata']['uid']='uid-'+target+'-'+resource['metadata']['name']
                    if copied['kind']=='PersistentVolumeClaim':copied['spec']['volumeName']='pv-'+target+'-'+copied['metadata']['name']
                    insert(copied)

if args[:2]==['config','view']:output('https://fixture.internal:6443')
if args[0]=='patch':
    obj=state[key(kindmap[args[1]],args[2],ns)]
    if state.get('inject_runtime_conflict') and obj['kind']=='ConfigMap':
        obj['metadata']['resourceVersion']=str(int(obj['metadata']['resourceVersion'])+1)
        state_path.write_text(json.dumps(state))
    patch=json.loads(args[args.index('-p')+1])
    for operation in patch:
        parts=operation['path'].strip('/').split('/');target=obj
        for part in parts[:-1]:target=target[part]
        if operation['op']=='test':
            if target.get(parts[-1])!=operation['value']:raise SystemExit('compare-and-swap refused')
        else:target[parts[-1]]=operation['value']
    obj['metadata']['resourceVersion']=str(int(obj['metadata']['resourceVersion'])+1)
    if obj['kind']=='GitRepository':obj['status']={'artifact':{'revision':obj['spec']['ref']['tag']+'@sha1:'+state['target_commit']}}
    output(obj)
if args[0]=='create':
    obj=json.load(sys.stdin);insert(obj);output(obj)
if args[0]=='wait' or args[:2]==['rollout','status']:output('ready')
if args[0]=='exec':output('a'*64+'  /payload/bytes')
if args[:3]==['delete','pod','velero-store-0']:
    pod=state[key('Pod','velero-store-0','velero-store')];pod['metadata']['uid']='store-reopened';output('deleted')
if args[0]!='get':raise SystemExit('unexpected mutation: '+str(args))
resource=args[1]
name=args[2] if len(args)>2 and not args[2].startswith('-') else None
if resource=='namespace' and name=='kube-system':output('cluster-fixture-uid')
if resource=='storageclass':output({'provisioner':'driver.longhorn.io','parameters':{'dataEngine':'v1','fsType':'ext4'}})
if resource in ('schedules','services','networkpolicies') or resource.startswith('pods,pvc,'):
    output({'items':[]})
if resource=='pvc' and not name:
    output({'items':[v for v in state.values() if isinstance(v,dict) and v.get('kind')=='PersistentVolumeClaim' and v['metadata']['namespace']==ns]})
if resource in ('datauploads','datadownloads'):
    restore=resource=='datadownloads';kind='Restore' if restore else 'Backup'
    label=args[args.index('-l')+1];uid=label.split('=')[1]
    op=next(v for v in state.values() if isinstance(v,dict) and v.get('kind')==kind and v['metadata']['uid']==uid)
    backup=state[key('Backup',op['spec']['backupName'],'velero')] if restore else op
    source=backup['spec']['includedNamespaces'][0]
    pvc=state[key('PersistentVolumeClaim','payload',source)]
    transfer={'metadata':{'namespace':'velero','name':'move-'+uid,'labels':{'velero.io/'+kind.lower()+'-uid':uid},'ownerReferences':[{'apiVersion':'velero.io/v1','kind':kind,'uid':uid,'name':op['metadata']['name']}]},'status':{'phase':'Completed','progress':{'bytesDone':8388608,'totalBytes':8388608}},'spec':{'backupStorageLocation':'local','sourceNamespace':source}}
    if restore:
        transfer['spec'].update(targetVolume={'namespace':op['spec']['namespaceMapping'][source],'pvc':'payload','pv':''},snapshotID='snapshot-'+backup['metadata']['uid'])
    else:
        transfer['metadata']['labels']['velero.io/pvc-uid']=pvc['metadata']['uid']
        transfer['status']['snapshotID']='snapshot-'+backup['metadata']['uid']
        transfer['spec'].update(sourcePVC='payload',snapshotType='CSI',csiSnapshot={'driver':'driver.longhorn.io'})
    if state.get('inject_wrong_uid'):transfer['metadata']['labels']['velero.io/'+kind.lower()+'-uid']='wrong'
    output({'items':[transfer]})
kind=kindmap.get(resource,resource)
obj=state.get(key(kind,name,ns))
if obj is None:
    if '--ignore-not-found' in args:output('')
    raise SystemExit('fixture missing: '+key(kind,name,ns))
output(obj)
