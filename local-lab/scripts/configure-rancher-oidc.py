#!/usr/bin/env python3
"""Configure Rancher Generic OIDC to authenticate through the local Keycloak realm.

Plan-only by default. Rancher 2.13+ supports programmatic Generic OIDC
configuration, which permits an unattended rebuild without the browser
authorization-code step of Rancher's Keycloak-specific provider setup.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

from tenant_catalog import load_catalog

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "local-lab/tenant-config/tenants.yaml"
DEFAULT_SECRETS = ROOT / ".secrets"
DEFAULT_SECRET = DEFAULT_SECRETS / "rancher-keycloak-client-secret"
DEFAULT_KUBECTL = DEFAULT_SECRETS / "kubectl"
DEFAULT_KUBECONFIG = DEFAULT_SECRETS / "rke2.yaml"
RENDERER_PATH = ROOT / "local-lab/scripts/render-tenant-foundation.py"
_spec = importlib.util.spec_from_file_location("tenant_foundation_renderer", RENDERER_PATH)
_renderer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_renderer)

AUTH_NAME = "genericoidc"
AUTH_TYPE = "genericOIDCConfig"
OWNER_LABEL = "platform.perkforge.io/managed-by"
OWNER_VALUE = "tenant-foundation"
RANCHER_URL = "https://rancher.local-lab.test"
RANCHER_REDIRECT_URL = f"{RANCHER_URL}/verify-auth"
KEYCLOAK_PUBLIC_REALM = "https://keycloak.local-lab.test/auth/realms/perkforge"
KEYCLOAK_INTERNAL_REALM = (
    "http://keycloak-keycloakx-http.keycloak.svc.cluster.local/auth/realms/perkforge"
)


def group_principals(catalog: dict) -> list[str]:
    values = []
    for tenant in catalog["tenants"]:
        for role in ("admins", "developers", "viewers"):
            path = tenant["identity"]["groups"].get(role)
            expected = f"/tenants/{tenant['id']}/{role}"
            if path != expected:
                raise ValueError(f"{tenant['id']}: expected Keycloak group path {expected}")
            values.append(f"genericoidc_group://{path}")
    return values


def auth_config(catalog: dict, client_secret: str) -> dict:
    if not client_secret or not client_secret.strip():
        raise ValueError("Rancher OIDC client secret is empty")
    return {
        "apiVersion": "management.cattle.io/v3",
        "kind": "AuthConfig",
        "metadata": {
            "name": AUTH_NAME,
            "labels": {OWNER_LABEL: OWNER_VALUE},
        },
        "type": AUTH_TYPE,
        "enabled": True,
        # Restricted allows explicitly authorized provider groups and project members.
        "accessMode": "restricted",
        "allowedPrincipalIds": group_principals(catalog),
        # Rancher's GenericOIDCConfig embeds OIDCConfig inline. These settings
        # belong at the AuthConfig root; a nested genericOIDCConfig object is
        # accepted as unknown data by the CRD but ignored by Rancher's provider.
        "clientId": "rancher",
        "clientSecret": client_secret,
        # Rancher requires the OIDC callback path here, while rancherApiHost
        # remains the public base URL used by its callback handler.
        "rancherUrl": RANCHER_REDIRECT_URL,
        "rancherApiHost": RANCHER_URL,
        "issuer": KEYCLOAK_PUBLIC_REALM,
        # Browser redirect remains public; server-to-server endpoints use cluster DNS.
        "authEndpoint": f"{KEYCLOAK_PUBLIC_REALM}/protocol/openid-connect/auth",
        "tokenEndpoint": f"{KEYCLOAK_INTERNAL_REALM}/protocol/openid-connect/token",
        "userInfoEndpoint": f"{KEYCLOAK_INTERNAL_REALM}/protocol/openid-connect/userinfo",
        "jwksUrl": f"{KEYCLOAK_INTERNAL_REALM}/protocol/openid-connect/certs",
        "scope": "openid profile email",
        "groupsClaim": "groups",
        "nameClaim": "preferred_username",
        "emailClaim": "email",
        "groupSearchEnabled": True,
        "clientAuthenticatedSearch": False,
    }


def validate_target(configs: list[dict], desired: dict) -> None:
    local = next((obj for obj in configs
                  if obj.get("metadata", {}).get("name") == "local"), None)
    if local is None or local.get("enabled") is not True:
        raise ValueError("Rancher local authentication must already be enabled; refusing OIDC activation")
    active = [obj.get("metadata", {}).get("name") for obj in configs
              if obj.get("enabled") is True and obj.get("metadata", {}).get("name")
              not in {"local", AUTH_NAME}]
    if active:
        raise ValueError("another external Rancher auth provider is enabled: " + ", ".join(active))
    current = next((obj for obj in configs
                    if obj.get("metadata", {}).get("name") == AUTH_NAME), None)
    if current is None:
        raise ValueError(f"Rancher AuthConfig {AUTH_NAME} is missing")
    current_has_settings = any(
        value not in (None, "", [], {})
        for key, value in current.items()
        if key not in {"apiVersion", "kind", "metadata", "status", "type",
                       "enabled", "accessMode", "allowedPrincipalIds",
                       "logoutAllSupported", "clientSecret"}
    )
    owned = current.get("metadata", {}).get("labels", {}).get(OWNER_LABEL) == OWNER_VALUE
    if current_has_settings and not owned:
        raise ValueError("Rancher Generic OIDC has unowned settings; refusing to replace them")
    if current.get("type") not in (None, AUTH_TYPE):
        raise ValueError(f"Rancher AuthConfig {AUTH_NAME} has unexpected type")
    if desired.get("type") != AUTH_TYPE:
        raise ValueError("desired Rancher auth provider type is invalid")


def nonsecret_errors(current: dict, expected: dict) -> list[str]:
    errors = []
    for field in ("type", "enabled", "accessMode", "allowedPrincipalIds"):
        if current.get(field) != expected.get(field):
            errors.append(field)
    for field, value in expected.items():
        if field == "clientSecret":
            continue
        if field in {"apiVersion", "kind", "metadata"}:
            continue
        if current.get(field) != value:
            errors.append(field)
    return errors


class Kubectl:
    def __init__(self, executable: str, kubeconfig: str | None, context: str | None):
        self.prefix = [executable]
        if kubeconfig:
            self.prefix += ["--kubeconfig", kubeconfig]
        if context:
            self.prefix += ["--context", context]

    def json(self, *args: str) -> dict:
        result = subprocess.run(self.prefix + list(args) + ["-o", "json"],
                                check=True, text=True, capture_output=True, timeout=90)
        return json.loads(result.stdout)

    def apply(self, document: dict, server_dry_run: bool = False) -> None:
        args = self.prefix + ["apply"]
        if server_dry_run:
            args.append("--dry-run=server")
        args += ["-f", "-"]
        result = subprocess.run(args, input=yaml.safe_dump(document, sort_keys=False),
                                text=True, capture_output=True, timeout=90)
        if result.returncode:
            # Avoid echoing an API error body that could contain submitted sensitive fields.
            raise RuntimeError("Rancher rejected the Generic OIDC configuration")


def reconcile(catalog: dict, secret_path: Path, kubectl: Kubectl,
              apply: bool = False, server_dry_run: bool = False) -> dict:
    _renderer.validate_catalog(catalog)
    if not secret_path.is_file():
        raise ValueError(f"Rancher OIDC client secret file is missing: {secret_path}")
    secret = secret_path.read_text().strip()
    desired = auth_config(catalog, secret)
    configs = kubectl.json("get", "authconfigs.management.cattle.io").get("items", [])
    validate_target(configs, desired)
    if apply or server_dry_run:
        kubectl.apply(desired, server_dry_run=server_dry_run)
    if apply:
        current = kubectl.json("get", "authconfigs.management.cattle.io", AUTH_NAME)
        errors = nonsecret_errors(current, desired)
        local = kubectl.json("get", "authconfigs.management.cattle.io", "local")
        if local.get("enabled") is not True:
            raise RuntimeError("Rancher local authentication became disabled; investigate immediately")
        if errors:
            raise RuntimeError("Rancher Generic OIDC postcondition failed for: " + ", ".join(errors))
    return desired


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--secret-file", type=Path, default=DEFAULT_SECRET)
    parser.add_argument("--kubectl", default=str(DEFAULT_KUBECTL))
    parser.add_argument("--kubeconfig", default=str(DEFAULT_KUBECONFIG))
    parser.add_argument("--context")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="enable Generic OIDC in Rancher")
    mode.add_argument("--server-dry-run", action="store_true",
                      help="validate the AuthConfig with the API server without persisting it")
    args = parser.parse_args()
    try:
        catalog = load_catalog(args.catalog)
        if not args.apply and not args.server_dry_run:
            _renderer.validate_catalog(catalog)
            if not args.secret_file.is_file():
                raise ValueError(f"Rancher OIDC client secret file is missing: {args.secret_file}")
            principals = group_principals(catalog)
            print(f"Plan: enable Rancher Generic OIDC through Keycloak for {len(principals)} tenant role groups.")
            print(f"Provider access mode: restricted; callback URL: {RANCHER_REDIRECT_URL}; local authentication remains enabled.")
            print("Plan only; no Rancher resources were changed. Use --apply after Keycloak is ready.")
            return 0
        kubectl = Kubectl(args.kubectl, args.kubeconfig, args.context)
        reconcile(catalog, args.secret_file, kubectl, args.apply, args.server_dry_run)
        if args.server_dry_run:
            print("Rancher accepted the Generic OIDC AuthConfig server dry-run; no resources were changed.")
        else:
            print("Rancher Generic OIDC is configured and enabled with restricted group access.")
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError,
            json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"Rancher OIDC configuration failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
