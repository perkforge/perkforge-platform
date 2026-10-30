"""Load inline or indexed tenant catalogs for all local-lab consumers."""
from pathlib import Path
import yaml


def load_catalog(path: Path) -> dict:
    """Resolve an explicit index without accepting arbitrary paths or YAML tags.

    Legacy inline catalogs remain supported for external callers and fixtures.
    Semantic validation across tenants is performed by validate_catalog.
    """
    path = Path(path)
    catalog = yaml.safe_load(path.read_text())
    if not isinstance(catalog, dict):
        raise ValueError('Tenant catalog must be a mapping')
    if 'tenantFiles' not in catalog:
        return catalog
    if 'tenants' in catalog:
        raise ValueError('Use tenantFiles or tenants, not both')
    files = catalog.pop('tenantFiles')
    if not isinstance(files, list) or not files:
        raise ValueError('tenantFiles must be a non-empty list')
    tenants, seen = [], set()
    base = path.parent.resolve()
    for reference in files:
        if not isinstance(reference, str):
            raise ValueError('Each tenantFiles entry must be a relative YAML path')
        relative = Path(reference)
        if relative.is_absolute() or relative.parent != Path('tenants') or relative.suffix != '.yaml':
            raise ValueError('Tenant files must be tenants/<tenant-id>.yaml')
        source = (base / relative).resolve()
        if not source.is_relative_to(base) or source in seen:
            raise ValueError('Tenant file escapes catalog directory or is repeated')
        seen.add(source)
        tenant = yaml.safe_load(source.read_text())
        if not isinstance(tenant, dict) or tenant.get('id') != relative.stem:
            raise ValueError(f'{reference}: tenant id must match filename')
        tenants.append(tenant)
    catalog['tenants'] = tenants
    return catalog
