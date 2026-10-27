"""Render shared Helm templates locally; never install, contact a cluster, or apply."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

import yaml

CHART = Path(__file__).resolve().parents[1] / 'templates/tenant-foundation'


def render(section, **values):
    values['section'] = section
    with tempfile.TemporaryDirectory(prefix='tenant-render-') as directory:
        inputs = Path(directory) / 'values.json'
        inputs.write_text(json.dumps(values))
        command = [os.environ.get('HELM', 'helm'), 'template', 'tenant-foundation',
                   str(CHART), '--values', str(inputs), '--show-only',
                   f'templates/{section}.yaml']
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Helm template exceeded the 30-second limit") from exc
    if result.returncode:
        raise ValueError(f'Helm template failed: {result.stderr.strip()}')
    return [obj for obj in yaml.safe_load_all(result.stdout) if obj is not None]
