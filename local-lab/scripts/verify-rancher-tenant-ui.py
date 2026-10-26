#!/usr/bin/env python3
"""Verify Keycloak login and Rancher project/API access for a synthetic tenant.

This test is read-only. It does not save browser state, traces, screenshots,
cookies, access tokens, or response bodies to disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright is missing; install local-lab/requirements-e2e.txt", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PASSWORD = ROOT / ".secrets/tenant-alpha-viewers-password"
BASE_URL = "https://rancher.local-lab.test"
LOGIN_PATH = "/dashboard/auth/login"


class CheckFailure(RuntimeError):
    pass


def api_get(page, path: str) -> tuple[int, dict | None]:
    """GET a JSON API resource from the authenticated browser session."""
    result = page.evaluate(
        """async (path) => {
          const response = await fetch(path, {headers: {Accept: 'application/json'}});
          const contentType = response.headers.get('content-type') || '';
          let body = null;
          if (contentType.includes('application/json')) body = await response.json();
          return {status: response.status, body};
        }""",
        path,
    )
    return result["status"], result["body"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def run(args: argparse.Namespace) -> int:
    secret_path = args.password_file.expanduser()
    if not secret_path.is_file():
        print(f"Password file is missing: {secret_path}", file=sys.stderr)
        return 2
    password = secret_path.read_text().strip()
    if not password:
        print("Password file is empty", file=sys.stderr)
        return 2

    results: list[dict[str, str]] = []

    def check(test_id: str, passed: bool, expected: str, actual: str) -> None:
        results.append({"id": test_id, "status": "PASS" if passed else "FAIL",
                        "expected": expected, "actual": actual})

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(ignore_https_errors=args.allow_local_tls_bypass)
            page = context.new_page()
            page.goto(BASE_URL + LOGIN_PATH, wait_until="domcontentloaded", timeout=30_000)
            check("rancher-login-page", "Rancher" in page.title(),
                  "Rancher login page", page.title())

            page.get_by_role("button", name="Log in with OIDC").click(timeout=15_000)
            page.wait_for_url("http://keycloak.local-lab.test/**", timeout=20_000)
            check("keycloak-oidc-redirect", "keycloak.local-lab.test" in page.url,
                  "Keycloak realm login", "Keycloak realm login")

            page.get_by_role("textbox", name="Username or email").fill(args.username)
            page.get_by_role("textbox", name="Password").fill(password)
            page.get_by_role("button", name="Sign In").click()
            page.wait_for_url("**/dashboard/home", timeout=30_000)
            page.wait_for_load_state("domcontentloaded", timeout=15_000)
            check("tenant-rancher-dashboard-login", "Rancher" in page.title(),
                  "authenticated Rancher dashboard", page.title())

            status, projects = api_get(page, "/v3/projects")
            project_ids = {item.get("id") for item in (projects or {}).get("data", [])}
            alpha_id = "local:p-tenant-alpha-local"
            bravo_id = "local:p-tenant-bravo-local"
            check("tenant-project-list", status == 200 and alpha_id in project_ids
                  and bravo_id not in project_ids,
                  "Alpha visible and Bravo omitted", f"HTTP {status}; {len(project_ids)} visible project(s)")

            alpha_status, _ = api_get(page, f"/v3/projects/{alpha_id}")
            check("tenant-own-project-read", alpha_status == 200,
                  "Alpha project readable", f"HTTP {alpha_status}")
            bravo_status, _ = api_get(page, f"/v3/projects/{bravo_id}")
            check("cross-tenant-project-denied", bravo_status == 403,
                  "Bravo project access denied (HTTP 403)", f"HTTP {bravo_status}")

            alpha_pods, _ = api_get(page, "/k8s/clusters/local/api/v1/namespaces/tenant-alpha/pods")
            check("tenant-own-workloads-readable", alpha_pods == 200,
                  "Alpha pod list readable", f"HTTP {alpha_pods}")
            bravo_pods, _ = api_get(page, "/k8s/clusters/local/api/v1/namespaces/tenant-bravo/pods")
            check("cross-tenant-workloads-denied", bravo_pods == 403,
                  "Bravo pod list denied (HTTP 403)", f"HTTP {bravo_pods}")

            for tenant in ("tenant-alpha", "tenant-bravo"):
                status, _ = api_get(
                    page, f"/k8s/clusters/local/api/v1/namespaces/{tenant}/secrets")
                check(f"{tenant}-viewer-secret-list-denied", status == 403,
                      "secret listing denied to viewer (HTTP 403)", f"HTTP {status}")

            context.close()
            browser.close()
    except CheckFailure as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except (PlaywrightError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        # Do not print raw browser/network exceptions: they may include
        # authorization URLs, codes, state, or session-related response data.
        print(f"Browser verification stopped ({type(exc).__name__}); no session data was saved.",
              file=sys.stderr)
        return 1

    for result in results:
        print(f"{result['status']} {result['id']}: expected {result['expected']}; actual {result['actual']}")
    passed = sum(item["status"] == "PASS" for item in results)
    print(f"Result: {passed}/{len(results)} checks passed. Browser state was discarded.")
    if args.allow_local_tls_bypass:
        print("TLS note: local Rancher certificate verification was bypassed for this run only.")
    return 0 if passed == len(results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default="tenant-alpha-viewers")
    parser.add_argument("--password-file", type=Path, default=DEFAULT_PASSWORD)
    parser.add_argument(
        "--allow-local-tls-bypass", action="store_true",
        help="allow the lab's local Rancher certificate; use only for local-lab.test")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
