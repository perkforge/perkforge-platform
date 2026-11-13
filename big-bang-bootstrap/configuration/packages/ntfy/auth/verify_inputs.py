"""Offline validation only. Does not establish approvals, identity or native state."""
import re

class InvalidInputs(ValueError):
    pass

def verify(accounts, previous_managed, existing_users, approved_removals, approved_entitlements):
    def require(condition):
        if not condition: raise InvalidInputs('Invalid or unapproved ntfy auth input; values suppressed')
    slug=lambda x: isinstance(x,str) and re.fullmatch(r'[a-z][a-z0-9-]{0,63}',x)
    for names in [previous_managed,existing_users,approved_removals]:
        require(isinstance(names,list) and all(slug(x) for x in names) and len(names)==len(set(names)))
    require(set(previous_managed)<=set(existing_users))
    require(isinstance(accounts,list) and isinstance(approved_entitlements,dict))
    names=[];tokens=[]
    for a in accounts:
        require(isinstance(a,dict) and set(a)=={'username','kind','role','subject_id','approved','topics','password_hash','token'})
        require(a['approved'] is True and slug(a['username']) and a['username'] not in ('everyone','anonymous'))
        require(a['kind'] in ('publisher','subscriber'))
        if a['kind']=='publisher':
            require(a['role']=='service' and a['subject_id'] is None)
        else:
            require(a['role'] in ('tenant-admin','tenant-developer','platform-engineer'))
            require(isinstance(a['subject_id'],str) and re.fullmatch(r'[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}',a['subject_id']))
        require(isinstance(a['topics'],list) and a['topics'] and all(slug(t) for t in a['topics']) and len(a['topics'])==len(set(a['topics'])))
        principal=a['username'] if a['kind']=='publisher' else a['subject_id']
        grant=approved_entitlements.get(principal)
        require(isinstance(grant,dict) and set(grant)=={'kind','role','topics'})
        require(grant['kind']==a['kind'] and grant['role']==a['role'])
        require(isinstance(grant['topics'],list) and all(slug(t) for t in grant['topics']))
        require(set(a['topics'])<=set(grant['topics']))
        require(isinstance(a['password_hash'],str) and re.fullmatch(r'\$2[aby]\$(10|11|12|13|14|15|16)\$[./A-Za-z0-9]{53}',a['password_hash']))
        require(isinstance(a['token'],str) and re.fullmatch(r'tk_[a-z0-9]{29}',a['token']))
        names.append(a['username']);tokens.append(a['token'])
    require(len(names)==len(set(names)) and len(tokens)==len(set(tokens)))
    require(not ((set(names)&set(existing_users))-set(previous_managed)))
    require(set(previous_managed)-set(names)==set(approved_removals))
    return True
