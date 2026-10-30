"""Shared released-source/context fixtures, with no network calls at import."""
import os,re,json,subprocess
from pathlib import Path
import yaml
EXAMPLES=Path(__file__).resolve().parents[2]
PREFIX='example.perkforge.io/'
KEYS=('cluster','environment','profile')
def build(path):
    output = subprocess.check_output(
        ["kubectl", "kustomize", str(path)], text=True,
        env={**os.environ, "KUBECONFIG": "/dev/null"},
    )
    return [obj for obj in yaml.safe_load_all(output) if obj]

def release_for(source, evidence):
    assert source['spec']['ref'] == {'tag': evidence['tag']}
    assert re.fullmatch(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', evidence['tag'])
    assert re.fullmatch(r'[0-9a-f]{40}', evidence['resolvedCommit'])
    assert source['spec']['url'] == f"https://github.com/{evidence['repository']}.git"
    return evidence

def context(obj):
    annotations = obj["metadata"]["annotations"]
    return {key: annotations[PREFIX + key] for key in KEYS}
