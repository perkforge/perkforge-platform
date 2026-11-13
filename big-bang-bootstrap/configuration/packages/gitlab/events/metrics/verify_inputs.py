"""Offline verification only; actual templates rendered by Ansible during future setup."""
import re
from urllib.parse import urlsplit


def verify(values):
    def require(ok):
        if not ok:
            raise ValueError('Invalid inactive GitLab metrics input')
    def text(value):
        return isinstance(value, str) and bool(value) and all(ord(c) >= 32 for c in value)
    require(values['approved'] is True)
    require(re.fullmatch(r'[a-z][a-z0-9-]*', values['context_id']))
    require(type(values['grafana_org_id']) is int and values['grafana_org_id'] > 0)
    require(re.fullmatch(r'[A-Za-z0-9_-]+', values['prometheus_uid']))
    url = urlsplit(values['gitlab_url'])
    require(url.scheme == 'https' and url.hostname and not url.username and not url.password
            and not url.query and not url.fragment and url.path in ('', '/'))
    projects = values['metric_projects']
    require(isinstance(projects, list) and bool(projects))
    ids, paths = {}, set()
    for project in projects:
        require(type(project['id']) is int and project['id'] > 0 and project['id'] not in ids)
        require(re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+', project['path']))
        require(project['path'] not in paths)
        for key in ('refs', 'environments'):
            require(isinstance(project[key], list) and all(text(v) for v in project[key]))
            require(len(set(project[key])) == len(project[key]))
        require(bool(project['refs']))
        ids[project['id']] = project
        paths.add(project['path'])
    require(isinstance(values['metric_incidents'], list) and bool(values['metric_incidents']))
    uids = set()
    metrics = {'pipeline': ('gitlab_ci_pipeline_status', {'ref', 'kind', 'source'}),
               'security_scan_execution': ('gitlab_ci_pipeline_job_status', {'ref', 'kind', 'source', 'stage', 'job_name'})}
    for incident in values['metric_incidents']:
        require(re.fullmatch(r'[a-z][a-z0-9-]{0,39}', incident['uid']) and incident['uid'] not in uids)
        uids.add(incident['uid'])
        require(type(incident['project_id']) is int and incident['project_id'] in ids)
        project = ids[incident['project_id']]
        require(incident['project_path'] == project['path'])
        require(incident['event_class'] in metrics)
        metric, keys = metrics[incident['event_class']]
        require(incident['metric'] == metric and set(incident['selectors']) == keys)
        require(all(text(v) for v in incident['selectors'].values()))
        if 'ref' in keys:
            require(incident['selectors']['ref'] in project['refs'] and incident['selectors']['kind'] == 'branch')
        else:
            require(incident['selectors']['environment'] in project['environments'])
