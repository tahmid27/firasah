"""Structural guards for auth coverage and BigQuery access."""

import ast
import re
from pathlib import Path

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import main
from api.auth import get_signing_keys
from api.settings import get_settings
from api.tenancy import get_org_context
from tests.api_helpers import SETTINGS, FakeSigningKeys

PUBLIC_ROUTES = {
    "/health",  # uptime checks
    "/auth/tiktok/callback",  # called by TikTok's servers during OAuth
}


def _dependency_calls(dependant):
    """Every function in a route's dependency tree."""
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _dependency_calls(dependency)


def _api_routes(routes=None):
    """Every APIRoute, including those inside included routers."""
    for route in main.app.routes if routes is None else routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "original_router"):
            if route.include_context.prefix:
                raise AssertionError("include prefixes aren't handled here")
            yield from _api_routes(route.original_router.routes)


def _spec_operations():
    """(method, path) for every operation in the app's OpenAPI spec."""
    return {
        (method.upper(), path)
        for path, operations in main.app.openapi()["paths"].items()
        for method in operations
    }


def test_route_discovery_sees_every_endpoint_in_the_spec():
    discovered = {
        (method, route.path) for route in _api_routes() for method in route.methods
    }
    assert discovered == _spec_operations()


def test_every_non_public_route_requires_a_resolved_charity():
    unprotected = [
        f"{sorted(route.methods)} {route.path}"
        for route in _api_routes()
        if route.path not in PUBLIC_ROUTES
        and get_org_context not in set(_dependency_calls(route.dependant))
    ]

    assert unprotected == [], (
        "routes missing the auth/org dependency (declare `ctx: CurrentOrg` "
        f"or depend on the Warehouse): {unprotected}"
    )


def test_every_non_public_endpoint_refuses_an_anonymous_request():
    main.app.dependency_overrides = {
        get_settings: lambda: SETTINGS,
        get_signing_keys: lambda: FakeSigningKeys(),
    }
    client = TestClient(main.app)
    let_through = []
    for method, path in sorted(_spec_operations()):
        if path in PUBLIC_ROUTES:
            continue
        response = client.request(method, re.sub(r"\{[^}]+\}", "x", path))
        if response.status_code != 401:
            let_through.append(f"{method} {path} -> {response.status_code}")

    main.app.dependency_overrides = {}
    assert let_through == []


def test_public_route_list_has_no_stale_entries():
    assert PUBLIC_ROUTES <= {path for _, path in _spec_operations()}


def test_at_least_one_protected_route_exists():
    assert any(path not in PUBLIC_ROUTES for _, path in _spec_operations())


def test_only_the_query_helper_touches_bigquery():
    allowed = Path("api/warehouse.py")
    offenders = []
    for path in [*Path("api").rglob("*.py"), Path("main.py")]:
        if path == allowed:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            imports_bigquery = (
                isinstance(node, ast.ImportFrom)
                and (node.module or "").startswith("google.cloud")
                and any(a.name == "bigquery" for a in node.names)
            ) or (
                isinstance(node, ast.Import)
                and any(a.name.startswith("google.cloud.bigquery") for a in node.names)
            )
            runs_sql = (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "query"
            )
            if imports_bigquery or runs_sql:
                offenders.append(f"{path}:{node.lineno}")

    assert offenders == [], f"BigQuery used outside api/warehouse.py: {offenders}"
