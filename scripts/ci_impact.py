#!/usr/bin/env python3
"""Select offline CI suites conservatively; unknown/missing impact runs everything."""
import argparse
import json
import os
from pathlib import PurePosixPath
import re
import subprocess


def full(reason):
    return dict(full=True, sso=True, headlamp=True, docs=True, reason=reason)


def classify(paths, event='pull_request'):
    if event != 'pull_request':
        return full('non-PR event: full validation')
    if not isinstance(paths, list) or not paths:
        return full('empty or unavailable change list')
    result = dict(full=False, sso=False, headlamp=False, docs=True, reason='known isolated changes')
    for path in paths:
        if not isinstance(path,str) or not path or path.startswith('/') or any(ord(c)<32 for c in path) or '..' in PurePosixPath(path).parts:
            return full('unrecognized path')
        # Workflow, selector, shared fixtures/dependencies and every unknown path
        # deliberately hit full validation rather than an optimistic default.
        if path.startswith(('.github/', 'scripts/')) or path == 'AGENTS.md':
            return full('CI/shared policy changed')
        if path.startswith('docs/') or path in ('README.md','HANDOFF.md','CHANGELOG.md') or (path.endswith('/README.md') and path.startswith(('big-bang-bootstrap/','infrastructure/','pxe/','evidence/'))):
            continue
        if path == 'big-bang-bootstrap/configuration/authorization/MATRIX.md' or path.startswith('big-bang-bootstrap/configuration/authorization/sso/'):
            result.update(sso=True, headlamp=True)
            continue
        if path in ('big-bang-bootstrap/tests/security/test_platform_sso.py',) or re.fullmatch(r'big-bang-bootstrap/tests/(bootstrap|integration)/test_sso_[^/]+\.py',path) or re.fullmatch(r'big-bang-bootstrap/tests/fixtures/sso-[^/]+\.py',path):
            result.update(sso=True, headlamp=True)
            continue
        if path in ('infrastructure/ansible/playbooks/configure-api-oidc.yml', 'infrastructure/ansible/api-oidc.example.yml', 'infrastructure/ansible/tests/test_api_oidc.py', 'infrastructure/ansible/tests/api-oidc-cli.py', 'big-bang-bootstrap/tests/bootstrap/test_headlamp_routing.py') or re.fullmatch(r'infrastructure/ansible/tasks/api-oidc(?:-[^/]+)?\.yml',path):
            result['headlamp'] = True
            continue
        return full('shared dependency or unknown impact')
    return result


def changed_paths(base, head):
    if not all(re.fullmatch('[0-9a-f]{40}',ref or '') for ref in (base,head)):
        return None
    try:
        raw=subprocess.check_output(['git','diff','--no-renames','--name-only','-z',base,head,'--'],stderr=subprocess.DEVNULL)
        return [p.decode('utf-8') for p in raw.split(b'\0') if p]
    except (subprocess.CalledProcessError,UnicodeError):
        return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event',default=os.environ.get('CI_EVENT','unknown'))
    parser.add_argument('--base',default=os.environ.get('CI_BASE',''))
    parser.add_argument('--head',default=os.environ.get('CI_HEAD',''))
    args=parser.parse_args()
    decision=classify(changed_paths(args.base,args.head),args.event)
    print(json.dumps(decision,sort_keys=True))
    output=os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output,'a') as target:
            for key in ('full','sso','headlamp','docs'):
                target.write(f'{key}={str(decision[key]).lower()}\n')
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as target:
            target.write('### Offline validation selection\n\n'+decision['reason']+'\n\n')
            target.write(' | '.join(f'{key}: {str(decision[key]).lower()}' for key in ('full','sso','headlamp','docs'))+'\n')


if __name__=='__main__':main()
