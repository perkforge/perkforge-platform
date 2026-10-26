#!/usr/bin/env python3
"""Provision Keycloak tenant groups and the Rancher OIDC client."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "local-lab/tenant-config/tenants.yaml"
DEFAULT_SECRETS = ROOT / ".secrets"
DEFAULT_KUBECTL = DEFAULT_SECRETS / "kubectl"
DEFAULT_KUBECONFIG = DEFAULT_SECRETS / "rke2.yaml"
REALM = "perkforge"
CLIENT_ID = "rancher"
RANCHER_URL = "https://rancher.local-lab.test"
KEYCLOAK_PUBLIC_URL = "http://keycloak.local-lab.test/auth"
KEYCLOAK_INTERNAL_URL = "http://keycloak-keycloakx-http.keycloak.svc.cluster.local/auth"
OWNERSHIP_ATTRIBUTE = "perkforge-managed"


def group_paths(catalog: dict) -> list[str]:
    paths = []
    for tenant in catalog["tenants"]:
        for role in ("admins", "developers", "viewers"):
            expected = f"/tenants/{tenant['id']}/{role}"
            if tenant["identity"]["groups"].get(role) != expected:
                raise ValueError(f"{tenant['id']}: expected Keycloak group {expected}")
            paths.append(expected)
    return paths


def rancher_client(secret: str) -> dict:
    return {
        "clientId": CLIENT_ID,
        "name": "PerkForge Rancher",
        "description": "OIDC client managed by the PerkForge tenant catalog.",
        "protocol": "openid-connect",
        "enabled": True,
        "publicClient": False,
        "clientAuthenticatorType": "client-secret",
        "secret": secret,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "redirectUris": [f"{RANCHER_URL}/verify-auth"],
        "webOrigins": [RANCHER_URL],
        "attributes": {OWNERSHIP_ATTRIBUTE: "true"},
    }


def group_mapper() -> dict:
    return {
        "name": "groups",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-group-membership-mapper",
        "consentRequired": False,
        "config": {
            "claim.name": "groups",
            "full.path": "true",
            "id.token.claim": "true",
            "access.token.claim": "false",
            "userinfo.token.claim": "true",
            "jsonType.label": "String",
        },
    }


def rancher_client_errors(client: dict, expected_secret: str, current_secret: str,
                          mappers: list[dict]) -> list[str]:
    """Return differing field names without exposing credential values."""
    expected = rancher_client(expected_secret)
    fields = ("clientId", "protocol", "enabled", "publicClient", "clientAuthenticatorType",
              "standardFlowEnabled", "implicitFlowEnabled", "directAccessGrantsEnabled",
              "serviceAccountsEnabled", "redirectUris", "webOrigins")
    errors = [field for field in fields if client.get(field) != expected[field]]
    if client.get("attributes", {}).get(OWNERSHIP_ATTRIBUTE) != "true":
        errors.append("managed ownership attribute")
    if current_secret != expected_secret:
        errors.append("client secret")
    matching = [mapper for mapper in mappers if mapper.get("name") == "groups"]
    if len(matching) != 1:
        errors.append("groups mapper count")
    else:
        actual = matching[0]
        desired = group_mapper()
        for field in ("protocol", "protocolMapper", "consentRequired"):
            if actual.get(field) != desired[field]:
                errors.append(f"groups mapper {field}")
        if actual.get("config") != desired["config"]:
            errors.append("groups mapper config")
    return errors


def rancher_oidc_endpoints() -> dict[str, str]:
    """Separate browser-facing identity URLs from in-cluster backchannel URLs."""
    realm_url = f"{KEYCLOAK_PUBLIC_URL}/realms/{REALM}"
    internal_realm_url = f"{KEYCLOAK_INTERNAL_URL}/realms/{REALM}"
    return {
        "issuer": realm_url,
        "authEndpoint": f"{realm_url}/protocol/openid-connect/auth",
        "tokenEndpoint": f"{internal_realm_url}/protocol/openid-connect/token",
        "userInfoEndpoint": f"{internal_realm_url}/protocol/openid-connect/userinfo",
        "jwksUrl": f"{internal_realm_url}/protocol/openid-connect/certs",
    }


def synthetic_identities(catalog: dict) -> list[tuple[str, str, str]]:
    return [
        (tenant["id"], role, f"{tenant['id']}-{role}")
        for tenant in catalog["tenants"]
        for role in ("admins", "developers", "viewers")
    ]


class KeycloakAdmin:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        token_url = f"{self.base_url}/realms/master/protocol/openid-connect/token"
        body = urllib.parse.urlencode({
            "client_id": "admin-cli",
            "username": username,
            "password": password,
            "grant_type": "password",
        }).encode()
        response = self._request("POST", token_url, body=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.token = json.loads(response)["access_token"]

    def _request(self, method: str, url: str, body: bytes | None = None,
                 headers: dict | None = None, accepted: tuple[int, ...] = (200,)) -> bytes:
        request_headers = dict(headers or {})
        if hasattr(self, "token"):
            request_headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status not in accepted:
                    raise RuntimeError(f"Keycloak API returned HTTP {response.status}")
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in accepted:
                return exc.read()
            # Do not include response bodies: provider errors can echo submitted data.
            raise RuntimeError(f"Keycloak API request failed with HTTP {exc.code}") from None
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Keycloak API is unavailable: {exc.reason}") from None

    def api(self, method: str, path: str, value: dict | None = None,
            accepted: tuple[int, ...] = (200,)) -> bytes:
        body = json.dumps(value).encode() if value is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        return self._request(method, f"{self.base_url}/admin{path}", body, headers, accepted)

    def ensure_realm(self) -> None:
        path = f"/realms/{REALM}"
        try:
            realm = json.loads(self.api("GET", path))
        except RuntimeError as exc:
            if "HTTP 404" not in str(exc):
                raise
            self.api("POST", "/realms", {
                "realm": REALM,
                "enabled": True,
                "attributes": {OWNERSHIP_ATTRIBUTE: "true"},
            }, accepted=(201,))
            return
        if realm.get("attributes", {}).get(OWNERSHIP_ATTRIBUTE) != "true":
            raise RuntimeError(f"realm {REALM!r} exists but is not marked as PerkForge-managed")
        if realm.get("enabled") is not True:
            realm["enabled"] = True
            self.api("PUT", path, realm, accepted=(204,))

    def ensure_group_path(self, path: str) -> str:
        parent_id = None
        segments = path.strip("/").split("/")
        tenant_id, role = segments[1], segments[2]
        for index, segment in enumerate(segments):
            if parent_id is None:
                query = urllib.parse.urlencode({"search": segment, "exact": "true"})
                children = json.loads(self.api("GET", f"/realms/{REALM}/groups?{query}"))
                create_path = f"/realms/{REALM}/groups"
            else:
                query = urllib.parse.urlencode({"search": segment, "exact": "true"})
                children = json.loads(self.api(
                    "GET", f"/realms/{REALM}/groups/{parent_id}/children?{query}"))
                create_path = f"/realms/{REALM}/groups/{parent_id}/children"
            exact = [group for group in children if group.get("name") == segment]
            if len(exact) > 1:
                raise RuntimeError(f"multiple Keycloak groups named {segment!r} at {path!r}")
            if exact:
                group = exact[0]
                if group.get("attributes", {}).get(OWNERSHIP_ATTRIBUTE) != ["true"]:
                    raise RuntimeError(f"group {path!r} already exists without PerkForge ownership metadata")
                if index == len(segments) - 1:
                    group_attributes = group.get("attributes", {})
                    expected_identity = {"platform-tenant": [tenant_id], "platform-role": [role]}
                    if any(key in group_attributes and group_attributes[key] != value
                           for key, value in expected_identity.items()):
                        raise RuntimeError(f"group {path!r} has conflicting tenant/role ownership")
                    if any(group_attributes.get(key) != value
                           for key, value in expected_identity.items()):
                        group_attributes.update(expected_identity)
                        group["attributes"] = group_attributes
                        self.api("PUT", f"/realms/{REALM}/groups/{group['id']}",
                                 group, accepted=(204,))
            else:
                attributes = {OWNERSHIP_ATTRIBUTE: ["true"]}
                if index == len(segments) - 1:
                    attributes.update({"platform-tenant": [tenant_id], "platform-role": [role]})
                payload = {"name": segment, "attributes": attributes}
                self.api("POST", create_path, payload, accepted=(201,))
                refreshed = json.loads(self.api("GET", create_path))
                exact = [group for group in refreshed if group.get("name") == segment]
                if len(exact) != 1:
                    raise RuntimeError(f"Keycloak did not return the created group {path!r}")
                group = exact[0]
            parent_id = group["id"]
        return parent_id

    def ensure_user(self, tenant_id: str, role: str, username: str,
                    group_id: str, password_file: Path) -> None:
        query = urllib.parse.urlencode({"username": username, "exact": "true"})
        users = json.loads(self.api("GET", f"/realms/{REALM}/users?{query}"))
        users = [user for user in users if user.get("username") == username]
        if len(users) > 1:
            raise RuntimeError(f"multiple Keycloak users use username {username!r}")
        created = not users
        if created:
            user = {
                "username": username,
                "email": f"{username}@example.invalid",
                "firstName": tenant_id,
                "lastName": role,
                "enabled": True,
                "emailVerified": True,
                "attributes": {
                    OWNERSHIP_ATTRIBUTE: ["true"],
                    "platform-tenant": [tenant_id],
                    "platform-role": [role],
                },
            }
            self.api("POST", f"/realms/{REALM}/users", user, accepted=(201,))
            users = json.loads(self.api("GET", f"/realms/{REALM}/users?{query}"))
            users = [user for user in users if user.get("username") == username]
            if len(users) != 1:
                raise RuntimeError(f"Keycloak did not return the created user {username!r}")
        user = users[0]
        attributes = user.get("attributes", {})
        if attributes.get(OWNERSHIP_ATTRIBUTE) != ["true"] or \
                attributes.get("platform-tenant") != [tenant_id] or \
                attributes.get("platform-role") != [role]:
            raise RuntimeError(f"user {username!r} exists but is not owned by this tenant catalog")
        if user.get("enabled") is not True:
            user["enabled"] = True
            self.api("PUT", f"/realms/{REALM}/users/{user['id']}", user, accepted=(204,))

        password_needs_setting = created or not password_file.is_file()
        if password_file.is_file():
            os.chmod(password_file, 0o600)
            password = password_file.read_text().strip()
            if not password:
                raise RuntimeError(f"synthetic user password file is empty: {password_file}")
        else:
            password = secrets.token_urlsafe(32)
            write_secret(password_file, password)
        if password_needs_setting:
            payload = {"type": "password", "value": password, "temporary": False}
            self.api("PUT", f"/realms/{REALM}/users/{user['id']}/reset-password",
                     payload, accepted=(204,))

        memberships = json.loads(self.api("GET", f"/realms/{REALM}/users/{user['id']}/groups"))
        for current_group in memberships:
            group_attributes = current_group.get("attributes", {})
            if group_attributes.get(OWNERSHIP_ATTRIBUTE) == ["true"] and \
                    group_attributes.get("platform-tenant") and group_attributes.get("platform-role") and \
                    current_group.get("id") != group_id:
                self.api("DELETE", f"/realms/{REALM}/users/{user['id']}/groups/"
                         f"{current_group['id']}", accepted=(204,))
        if not any(group.get("id") == group_id for group in memberships):
            self.api("PUT", f"/realms/{REALM}/users/{user['id']}/groups/{group_id}",
                     accepted=(204,))

    def ensure_client(self, secret: str | None) -> str:
        query = urllib.parse.urlencode({"clientId": CLIENT_ID})
        clients = json.loads(self.api("GET", f"/realms/{REALM}/clients?{query}"))
        clients = [client for client in clients if client.get("clientId") == CLIENT_ID]
        if len(clients) > 1:
            raise RuntimeError(f"multiple Keycloak clients use clientId {CLIENT_ID!r}")
        if not clients:
            secret = secret or secrets.token_urlsafe(48)
            desired = rancher_client(secret)
            self.api("POST", f"/realms/{REALM}/clients", desired, accepted=(201,))
            clients = json.loads(self.api("GET", f"/realms/{REALM}/clients?{query}"))
            clients = [client for client in clients if client.get("clientId") == CLIENT_ID]
            if len(clients) != 1:
                raise RuntimeError("Keycloak did not return the created Rancher client")
        client = clients[0]
        if client.get("attributes", {}).get(OWNERSHIP_ATTRIBUTE) != "true":
            raise RuntimeError(f"client {CLIENT_ID!r} exists but is not marked as PerkForge-managed")
        if secret is None:
            secret_response = json.loads(self.api(
                "GET", f"/realms/{REALM}/clients/{client['id']}/client-secret"))
            secret = secret_response.get("value")
            if not secret:
                raise RuntimeError("Keycloak returned no secret for the managed Rancher client")
        desired = rancher_client(secret)
        client.update({key: value for key, value in desired.items()
                       if key != "attributes" and key != "secret"})
        attributes = client.get("attributes", {})
        attributes[OWNERSHIP_ATTRIBUTE] = "true"
        client["attributes"] = attributes
        client["secret"] = secret
        self.api("PUT", f"/realms/{REALM}/clients/{client['id']}", client, accepted=(204,))
        client_id = client["id"]
        mappers = json.loads(self.api(
            "GET", f"/realms/{REALM}/clients/{client_id}/protocol-mappers/models"))
        matching = [mapper for mapper in mappers if mapper.get("name") == "groups"]
        if len(matching) > 1:
            raise RuntimeError("multiple protocol mappers named 'groups' exist on the Rancher client")
        desired_mapper = group_mapper()
        if matching:
            mapper = matching[0]
            if mapper.get("protocolMapper") != desired_mapper["protocolMapper"]:
                raise RuntimeError("Rancher client has an incompatible mapper named 'groups'")
            desired_mapper["id"] = mapper["id"]
            self.api("PUT", f"/realms/{REALM}/clients/{client_id}/protocol-mappers/models/{mapper['id']}",
                     desired_mapper, accepted=(204,))
        else:
            self.api("POST", f"/realms/{REALM}/clients/{client_id}/protocol-mappers/models",
                     desired_mapper, accepted=(201,))
        saved_clients = json.loads(self.api("GET", f"/realms/{REALM}/clients?{query}"))
        saved_clients = [saved for saved in saved_clients if saved.get("clientId") == CLIENT_ID]
        if len(saved_clients) != 1:
            raise RuntimeError("Keycloak did not return exactly one configured Rancher client")
        saved_secret = json.loads(self.api(
            "GET", f"/realms/{REALM}/clients/{client_id}/client-secret")).get("value", "")
        saved_mappers = json.loads(self.api(
            "GET", f"/realms/{REALM}/clients/{client_id}/protocol-mappers/models"))
        errors = rancher_client_errors(saved_clients[0], secret, saved_secret, saved_mappers)
        if errors:
            raise RuntimeError("Rancher OIDC client verification failed for: " + ", ".join(errors))
        return secret


def write_secret(path: Path, value: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(value + "\n")
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def choose_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_keycloak(base_url: str, process: subprocess.Popen, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    discovery = f"{base_url}/realms/master/.well-known/openid-configuration"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("kubectl port-forward exited before Keycloak became reachable")
        try:
            with urllib.request.urlopen(discovery, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise RuntimeError("Keycloak did not become reachable through kubectl port-forward")


def configure(args: argparse.Namespace, catalog: dict) -> None:
    secrets_dir = args.secrets_dir
    admin_password_file = secrets_dir / "keycloak-admin-password"
    client_secret_file = secrets_dir / "rancher-keycloak-client-secret"
    if not admin_password_file.is_file():
        raise RuntimeError(f"missing Keycloak admin password file: {admin_password_file}")
    if not args.kubeconfig.is_file() or not args.kubectl.is_file():
        raise RuntimeError("local-lab kubectl or kubeconfig is missing from .secrets/")
    os.chmod(secrets_dir, 0o700)
    os.chmod(admin_password_file, 0o600)

    port = args.local_port or choose_port()
    if not 1 <= port <= 65535:
        raise ValueError("local port must be between 1 and 65535")
    port_forward_log = secrets_dir / "keycloak-port-forward.log"
    with port_forward_log.open("w") as log_file:
        os.chmod(port_forward_log, 0o600)
        process = subprocess.Popen(
            [str(args.kubectl), "--kubeconfig", str(args.kubeconfig), "-n", "keycloak",
             "port-forward", "--address", "127.0.0.1", f"service/{args.service}", f"{port}:80"],
            stdout=log_file, stderr=subprocess.STDOUT,
        )
    try:
        base_url = f"http://127.0.0.1:{port}/auth"
        try:
            wait_for_keycloak(base_url, process)
        except RuntimeError as exc:
            raise RuntimeError(f"{exc}; see {port_forward_log}") from None
        admin_password = admin_password_file.read_text().strip()
        admin = KeycloakAdmin(base_url, args.admin_username, admin_password)
        admin.ensure_realm()

        if client_secret_file.is_file():
            os.chmod(client_secret_file, 0o600)
            client_secret = client_secret_file.read_text().strip()
            if not client_secret:
                raise RuntimeError(f"client secret file is empty: {client_secret_file}")
        else:
            client_secret = None

        client_secret = admin.ensure_client(client_secret)
        if not client_secret_file.is_file():
            write_secret(client_secret_file, client_secret)
        for tenant_id, role, username in synthetic_identities(catalog):
            path = f"/tenants/{tenant_id}/{role}"
            group_id = admin.ensure_group_path(path)
            password_file = secrets_dir / f"{username}-password"
            admin.ensure_user(tenant_id, role, username, group_id, password_file)
        print(f"Configured Keycloak realm {REALM!r}, Rancher OIDC client, and "
              f"{len(group_paths(catalog))} catalog groups and {len(synthetic_identities(catalog))} "
              "synthetic tenant accounts.")
        print(f"Rancher client secret stored at {client_secret_file} (value not shown).")
        print(f"Synthetic account credentials are stored under {secrets_dir} (values not shown).")
        print("Rancher's Keycloak OIDC provider remains a separate activation and login-validation step.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--apply", action="store_true",
                        help="connect to Keycloak and reconcile the realm, client, and groups")
    parser.add_argument("--secrets-dir", type=Path, default=DEFAULT_SECRETS)
    parser.add_argument("--kubectl", type=Path, default=DEFAULT_KUBECTL)
    parser.add_argument("--kubeconfig", type=Path, default=DEFAULT_KUBECONFIG)
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--service", default="keycloak-keycloakx-http")
    parser.add_argument("--local-port", type=int, default=0,
                        help="local port for the loopback-only port-forward (0 selects a free port)")
    args = parser.parse_args()
    try:
        catalog = yaml.safe_load(args.catalog.read_text())
        group_list = group_paths(catalog)
        if args.apply:
            configure(args, catalog)
        else:
            print(f"Plan: Keycloak realm {REALM}; confidential OIDC client {CLIENT_ID};")
            print(f"      redirect URI {RANCHER_URL}/verify-auth; groups claim contains full paths.")
            print("      browser endpoints use keycloak.local-lab.test; Rancher backchannel uses the in-cluster service.")
            print("Groups to ensure:")
            for group in group_list:
                print(f"  {group}")
            print("Synthetic accounts:")
            for _, _, username in synthetic_identities(catalog):
                print(f"  {username}")
            print("Plan only; no cluster or Keycloak resources were changed. Use --apply to reconcile.")
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, yaml.YAMLError,
            subprocess.CalledProcessError) as exc:
        print(f"Keycloak tenant configuration failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
