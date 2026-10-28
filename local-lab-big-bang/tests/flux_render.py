"""Exercise the real Ansible/Kustomize assembly as an offline test fixture."""
from pathlib import Path
import os
import subprocess
import tempfile

import yaml


def render_flux(sources, examples, profile):
    with tempfile.TemporaryDirectory() as directory:
        result_path = Path(directory) / 'rendered.yaml'
        tasks = [
            {'ansible.builtin.include_tasks': str(examples / 'ansible/prepare-flux.yaml')},
            {'ansible.builtin.command': {'argv': ['kubectl', 'kustomize', '{{ flux_manifest_path }}']},
             'register': 'built', 'changed_when': False},
            {'ansible.builtin.copy': {'content': '{{ built.stdout }}', 'dest': str(result_path), 'mode': '0600'}},
            {'ansible.builtin.file': {'path': '{{ flux_staging.path }}', 'state': 'absent'},
             'when': 'flux_staging is defined and flux_staging.path is defined'},
        ]
        play = [{'name': 'Offline native Flux assembly test only', 'hosts': 'bootstrap_clusters',
                 'gather_facts': False,
                 'vars': {'flux_checkout': str(sources / 'bigbang'), 'flux_resource_profile': profile},
                 'tasks': tasks}]
        path = Path(directory) / 'test.yaml'
        path.write_text(yaml.safe_dump(play, sort_keys=False))
        command = ['ansible-playbook', '-i', str(examples / 'ansible/inventory.yaml'), str(path), '--limit', 'local']
        result = subprocess.run(command, text=True, capture_output=True,
            env={**os.environ, 'KUBECONFIG': '/dev/null', 'ANSIBLE_NOCOLOR': '1',
                 'ANSIBLE_LOCAL_TEMP': directory + '/local', 'ANSIBLE_REMOTE_TEMP': directory + '/remote'})
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return [obj for obj in yaml.safe_load_all(result_path.read_text()) if obj]
