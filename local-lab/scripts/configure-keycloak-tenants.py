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

from tenant_catalog import load_catalog

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "local-lab/tenant-config/tenants.yaml"
DEFAULT_SECRETS = ROOT / ".secrets"
DEFAULT_KUBECTL = DEFAULT_SECRETS / "kubectl"
DEFAULT_KUBECONFIG = DEFAULT_SECRETS / "rke2.yaml"
REALM = "perkforge"
CLIENT_ID = "rancher"
RANCHER_URL = "https://rancher.local-lab.test"
KEYCLOAK_PUBLIC_URL = "https://keycloak.local-lab.test/auth"
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


def portal_client(secret: str) -> dict:
    client = rancher_client(secret)
    client.update(clientId="household-portal", name="PerkForge household portal",
                  description="Platform-managed household portal; no administrative capabilities.",
                  redirectUris=["https://portal.local-lab.test/auth/callback"],
                  webOrigins=["https://portal.local-lab.test"], fullScopeAllowed=False)
    client["attributes"]["pkce.code.challenge.method"] = "S256"
    return client


def openbao_client(secret: str) -> dict:
    """Dedicated human login client; no users, memberships or administrative grants."""
    client = rancher_client(secret)
    client.update(clientId="openbao", name="PerkForge OpenBao",
                  description="Platform secrets human OIDC login",
                  redirectUris=["https://openbao.local-lab.test/ui/vault/auth/oidc/oidc/callback",
                                "http://localhost:8250/oidc/callback"],
                  webOrigins=["https://openbao.local-lab.test"], fullScopeAllowed=False,
                  defaultClientScopes=["profile"], optionalClientScopes=[])
    client["attributes"]["pkce.code.challenge.method"] = "S256"
    return client


def portal_mappers() -> list[dict]:
    groups = group_mapper()
    groups["config"]["access.token.claim"] = "true"
    return [groups, {
        "name": "portal-api-audience", "protocol": "openid-connect",
        "protocolMapper": "oidc-audience-mapper", "consentRequired": False,
        "config": {"included.custom.audience": "household-portal-api",
                   "access.token.claim": "true", "id.token.claim": "false"},
    }, {
        # The client has fullScopeAllowed=false and only tenant-reader in its
        # realm-role scope. Emit that resolved role at the API's required path.
        "name": "portal-api-roles", "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-realm-role-mapper", "consentRequired": False,
        "config": {"claim.name": "resource_access.household-portal-api.roles",
                   "jsonType.label": "String", "multivalued": "true",
                   "access.token.claim": "true", "id.token.claim": "false",
                   "userinfo.token.claim": "false", "introspection.token.claim": "false"},
    }]


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
            # Keycloak 26 adds this mapper option on save; keep its safe
            # disabled default explicit so the postcondition is idempotent.
            "introspection.token.claim": "false",
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
                        # A previous local setup may have created only the
                        # top-level /tenants container. Adopt that exact empty
                        # directory group, but never adopt populated groups or
                        # tenant/role groups without ownership metadata.
                        attributes = group.get("attributes", {})
                        safe_container = index == 0 and segment == "tenants" and not attributes
                        if safe_container:
                            members = json.loads(self.api(
                                "GET", f"/realms/{REALM}/groups/{group['id']}/members?max=1"))
                            safe_container = not members
                        if not safe_container:
                            raise RuntimeError(f"group {path!r} already exists without PerkForge ownership metadata")
                        group["attributes"] = {OWNERSHIP_ATTRIBUTE: ["true"]}
                        self.api("PUT", f"/realms/{REALM}/groups/{group['id']}",
                                 group, accepted=(204,))
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
            }
            self.api("POST", f"/realms/{REALM}/users", user, accepted=(201,))
            users = json.loads(self.api("GET", f"/realms/{REALM}/users?{query}"))
            users = [user for user in users if user.get("username") == username]
            if len(users) != 1:
                raise RuntimeError(f"Keycloak did not return the created user {username!r}")
        user = users[0]
        attributes = user.get("attributes", {})
        memberships = json.loads(self.api("GET", f"/realms/{REALM}/users/{user['id']}/groups"))
        member_group_ids = {group.get("id") for group in memberships}
        expected_identity = {
            OWNERSHIP_ATTRIBUTE: ["true"],
            "platform-tenant": [tenant_id],
            "platform-role": [role],
        }
        identity_marker_matches = all(attributes.get(key) == value
                                      for key, value in expected_identity.items())
        # Keycloak 26 ignores unmanaged user attributes by default. Ownership
        # is therefore established by the deterministic placeholder address
        # and membership in this catalog-owned tenant/role group, not by user
        # attributes. Empty legacy placeholders can be enrolled if they have
        # no other attributes or memberships.
        safe_synthetic_account = (
            not attributes
            and user.get("email") == f"{username}@example.invalid"
            and member_group_ids.issubset({group_id})
        )
        if not identity_marker_matches and not safe_synthetic_account:
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
        final_memberships = json.loads(self.api(
            "GET", f"/realms/{REALM}/users/{user['id']}/groups"))
        if not any(group.get("id") == group_id for group in final_memberships):
            raise RuntimeError(f"Keycloak did not retain user {username!r} in its catalog role group")

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

    def ensure_openbao_client(self) -> str:
        """Only the owned OpenBao client; no tenant lifecycle or membership changes."""
        realm = json.loads(self.api("GET", f"/realms/{REALM}"))
        if realm.get("attributes", {}).get(OWNERSHIP_ATTRIBUTE) != "true":
            raise RuntimeError("OpenBao requires the existing managed realm")
        query = "clientId=openbao"
        clients = json.loads(self.api("GET", f"/realms/{REALM}/clients?{query}"))
        clients = [c for c in clients if c.get("clientId") == "openbao"]
        if len(clients) > 1:
            raise RuntimeError("Multiple OpenBao clients found")
        if clients:
            client = clients[0]
            if client.get("attributes", {}).get(OWNERSHIP_ATTRIBUTE) != "true":
                raise RuntimeError("Existing OpenBao client is not platform-owned")
            path = f"/realms/{REALM}/clients/{client['id']}"
            mappers = json.loads(self.api("GET", path + "/protocol-mappers/models"))
            if len(mappers) > 1 or any(m.get("name") != "groups" or
                    m.get("protocolMapper") != group_mapper()["protocolMapper"] for m in mappers):
                raise RuntimeError("Unexpected OpenBao mapper; review before changing")
            scope = json.loads(self.api("GET", path + "/scope-mappings"))
            if scope.get("realmMappings") or scope.get("clientMappings"):
                raise RuntimeError("Unexpected OpenBao role scope; review before changing")
            secret = json.loads(self.api("GET", path + "/client-secret")).get("value")
            if not secret:
                raise RuntimeError("Managed OpenBao client secret is missing; refusing rotation")
        else:
            secret = secrets.token_urlsafe(48)
            self.api("POST", f"/realms/{REALM}/clients", openbao_client(secret), accepted=(201,))
            clients = json.loads(self.api("GET", f"/realms/{REALM}/clients?{query}"))
            clients = [c for c in clients if c.get("clientId") == "openbao"]
            if len(clients) != 1:
                raise RuntimeError("Created OpenBao client could not be uniquely verified")
            client = clients[0]
            path = f"/realms/{REALM}/clients/{client['id']}"
            mappers = []
        desired = openbao_client(secret)
        client.update(desired)
        self.api("PUT", path, client, accepted=(204,))
        mapper = group_mapper()
        if mappers:
            self.api("PUT", path + "/protocol-mappers/models/" + mappers[0]["id"],
                     {**mapper, "id":mappers[0]["id"]}, accepted=(204,))
        else:
            self.api("POST", path + "/protocol-mappers/models", mapper, accepted=(201,))
        saved = json.loads(self.api("GET", path))
        for key, value in desired.items():
            if key == "secret":
                continue
            if key == "attributes":
                if any(saved.get(key, {}).get(k) != v for k, v in value.items()):
                    raise RuntimeError("OpenBao PKCE/ownership verification failed")
            elif saved.get(key) != value:
                raise RuntimeError("OpenBao client verification failed for " + key)
        saved_mappers = json.loads(self.api("GET", path + "/protocol-mappers/models"))
        if len(saved_mappers) != 1 or any(saved_mappers[0].get(k) != v for k,v in mapper.items()):
            raise RuntimeError("OpenBao groups mapper verification failed")
        saved_secret = json.loads(self.api("GET", path + "/client-secret")).get("value")
        if saved_secret != secret:
            raise RuntimeError("OpenBao client secret verification failed")
        return secret

    def ensure_portal_client(self) -> str:
        """Only reconcile the portal client and Home reader grant; no Rancher/users changes."""
        realm = json.loads(self.api("GET", f"/realms/{REALM}"))
        if realm.get("attributes", {}).get(OWNERSHIP_ATTRIBUTE) != "true":
            raise RuntimeError("Portal requires the existing managed realm")
        query = "clientId=household-portal"
        clients = json.loads(self.api("GET", f"/realms/{REALM}/clients?{query}"))
        clients = [c for c in clients if c.get("clientId") == "household-portal"]
        if len(clients) > 1:
            raise RuntimeError("Multiple portal clients found")
        if clients:
            client = clients[0]
            if client.get("attributes", {}).get(OWNERSHIP_ATTRIBUTE) != "true":
                raise RuntimeError("Existing portal client is not platform-owned")
            secret = json.loads(self.api("GET", f"/realms/{REALM}/clients/{client['id']}/client-secret"))["value"]
        else:
            secret = secrets.token_urlsafe(48)
            self.api("POST", f"/realms/{REALM}/clients", portal_client(secret), accepted=(201,))
            clients = json.loads(self.api("GET", f"/realms/{REALM}/clients?{query}"))
            if len(clients) != 1:
                raise RuntimeError("Created portal client could not be uniquely verified")
            client = clients[0]
        path = f"/realms/{REALM}/clients/{client['id']}"
        desired = portal_client(secret)
        client.update(desired)
        self.api("PUT", path, client, accepted=(204,))
        mappers = json.loads(self.api("GET", path + "/protocol-mappers/models"))
        desired_mappers = portal_mappers()
        if any(m.get("name") not in {d["name"] for d in desired_mappers} for m in mappers):
            raise RuntimeError("Unexpected portal-specific protocol mapper; review before changing")
        for desired_mapper in desired_mappers:
            matches = [m for m in mappers if m.get("name") == desired_mapper["name"]]
            if len(matches) > 1 or (matches and matches[0].get("protocolMapper") != desired_mapper["protocolMapper"]):
                raise RuntimeError("Conflicting portal mapper")
            if matches:
                self.api("PUT", path + "/protocol-mappers/models/" + matches[0]["id"],
                         {**desired_mapper, "id": matches[0]["id"]}, accepted=(204,))
            else:
                self.api("POST", path + "/protocol-mappers/models", desired_mapper, accepted=(201,))
        roles = json.loads(self.api("GET", f"/realms/{REALM}/roles"))
        matches = [r for r in roles if r.get("name") == "tenant-reader"]
        description = "PerkForge portal read-only API access"
        if not matches:
            self.api("POST", f"/realms/{REALM}/roles", {"name": "tenant-reader", "description": description}, accepted=(201,))
        role = json.loads(self.api("GET", f"/realms/{REALM}/roles/tenant-reader"))
        if role.get("description") != description or role.get("composite"):
            raise RuntimeError("Existing tenant-reader role is not the expected non-composite portal role")
        scope = json.loads(self.api("GET", path + "/scope-mappings"))
        if scope.get("clientMappings") or any(r.get("name") != "tenant-reader" for r in scope.get("realmMappings", [])):
            raise RuntimeError("Unexpected portal role scope; review before granting access")
        self.api("POST", path + "/scope-mappings/realm", [role], accepted=(204,))
        for name in ("admins", "developers", "viewers"):
            group_id = self.ensure_group_path(f"/tenants/home/{name}")
            self.api("POST", f"/realms/{REALM}/groups/{group_id}/role-mappings/realm", [role], accepted=(204,))
        saved = json.loads(self.api("GET", path))
        for key, value in desired.items():
            if key == "secret":
                continue
            if key == "attributes":
                if any(saved.get(key, {}).get(k) != v for k, v in value.items()):
                    raise RuntimeError("Portal PKCE/ownership verification failed")
            elif saved.get(key) != value:
                raise RuntimeError("Portal client verification failed for " + key)
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
        if args.openbao_only:
            secret = admin.ensure_openbao_client()
            write_secret(secrets_dir / "openbao-keycloak-client-secret", secret)
            print("Verified only OpenBao client/groups mapper; secret saved privately; no memberships changed.")
            return
        if args.portal_only:
            secret = admin.ensure_portal_client()
            write_secret(secrets_dir / "portal-keycloak-client-secret", secret)
            print("Verified portal client and Home tenant-reader grants; secret saved locally, value not shown.")
            return
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--openbao-only", action="store_true", help="only reconcile the owned OpenBao client; no users, groups or other clients")
    mode.add_argument("--portal-only", action="store_true", help="reconcile only portal client and Home reader grants; no users or Rancher client")
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
        catalog = load_catalog(args.catalog)
        group_list = group_paths(catalog)
        if args.apply:
            configure(args, catalog)
        elif args.openbao_only:
            print("Plan: existing managed realm; dedicated OpenBao confidential client; S256 PKCE;")
            print("      exact browser/localhost callbacks; full-path groups in ID token/userinfo;")
            print("      no users, memberships, role grants or other clients changed. No live action.")
        elif args.portal_only:
            print("Plan: managed perkforge realm; household-portal confidential client; S256 PKCE;")
            print("      exact https://portal.local-lab.test/auth/callback; household-portal-api audience;")
            print("      tenant-reader role only for existing Home groups; no users or Rancher changes.")
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
