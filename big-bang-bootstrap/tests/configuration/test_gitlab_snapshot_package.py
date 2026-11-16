"""Include the offline source-package checks in normal platform discovery."""
import importlib.util
from pathlib import Path

path = (Path(__file__).resolve().parents[2] /
        'configuration/packages/gitlab/events/collector/test_integrity.py')
spec = importlib.util.spec_from_file_location('snapshot_package_integrity', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SnapshotPackage(module.Integrity):
    """Exact source/license integrity and tamper refusal; no build or network."""
