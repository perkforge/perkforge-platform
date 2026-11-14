"""Emit actual rendered native CEL fixtures; invoked only by explicit offline test."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import yaml
sys.path.insert(0,str(Path(__file__).parent))
from integration.test_log_namespace_guard import inputs, render, UID

with tempfile.TemporaryDirectory() as temp:
    run=render(inputs(Path(temp)/'out'))
    if run.returncode: raise RuntimeError(run.stdout+run.stderr)
    policy=next(yaml.safe_load_all((Path(temp)/'out/policy.yaml').read_text()))
    old=inputs(Path(temp)/'unused')['log_namespace_observed']
    new=copy.deepcopy(old)
    new['metadata']['annotations'].update({'platform.perkforge.io/log-context':'portal','platform.perkforge.io/log-scope':'portal-runtime-v1'})
    cases=[]
    def case(name,operation,obj,prior,allowed):
        cases.append(dict(name=name,operation=operation,object=obj,oldObject=prior,allowed=allowed))
    case('initial_guarded_binding','UPDATE',new,old,True)
    case('unchanged_foundation_ssa','UPDATE',new,new,True)
    unrelated=copy.deepcopy(new);unrelated['metadata']['labels']['other']='preserved'
    case('unrelated_label_update','UPDATE',unrelated,new,True)
    case('delete_blocked','DELETE',None,new,False)
    case('create_reuse_blocked','CREATE',new,None,False)
    for key,value in [('uid','22222222-2222-4222-8222-222222222222'),('annotations',{}),('name','other')]:
        changed=copy.deepcopy(new);changed['metadata'][key]=value
        case('new_'+key+'_drift','UPDATE',changed,new,False)
    wrongold=copy.deepcopy(new);wrongold['metadata']['uid']='22222222-2222-4222-8222-222222222222'
    case('old_uid_rebound','UPDATE',new,wrongold,False)
    for key,value in [('platform.perkforge.io/log-context','other'),('platform.perkforge.io/log-scope','portal-runtime-v2')]:
        changed=copy.deepcopy(new);changed['metadata']['annotations'][key]=value
        case('owner_'+key.rsplit('/',1)[-1],'UPDATE',changed,new,False)
    print(json.dumps({'expression':policy['spec']['validations'][0]['expression'],'cases':cases}))
