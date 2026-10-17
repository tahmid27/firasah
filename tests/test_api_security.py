"""Structural guards: these fail the build when someone adds an endpoint that
skips auth, or runs BigQuery SQL outside the one query helper."""

import ast
from pathlib import Path

from fastapi.routing import APIRoute

import main
from api.tenancy import get_org_context

# Routes that are public on purpose. Adding to this list should be a
# deliberate, reviewed decision — that's the point of keeping it explicit.
PUBLIC_ROUTES = {
    "/health",  # uptime checks
    "/auth/tiktok/callback",  # called by TikTok's servers during OAuth
}


def _dependency_calls(dependant):
    """Every function in a route's dependency tree, however deeply nested."""
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _dependency_calls(dependency)


def _api_routes():
    return [r for r in main.app.routes if isinstance(r, APIRoute)]


def test_every_non_public_route_requires_a_resolved_charity():
    unprotected = [
        f"{sorted(route.methods)} {route.path}"
        for route in _api_routes()
        if route.path not in PUBLIC_ROUTES
        and get_org_context not in set(_dependency_calls(route.dependant))
    ]

    assert unprotected == [], (
        "routes missing the auth/org dependency (declare `ctx: CurrentOrg`): "
        f"{unprotected}"
    )


def test_public_route_list_has_no_stale_entries():
    # A removed route lingering here would silently pre-approve a future
    # route at the same path
    assert PUBLIC_ROUTES <= {route.path for route in _api_routes()}


def test_at_least_one_protected_route_exists():
    # Guards the guard: with no protected routes the main test passes vacuously
    assert any(route.path not in PUBLIC_ROUTES for route in _api_routes())


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
