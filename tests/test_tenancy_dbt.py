"""Tenant isolation at the dbt layer, checked statically from dbt's parsed
project (its "manifest") — no BigQuery connection needed, so it runs in CI.

Fails the build if a staging model or mart is added without an org_id column
and a not_null test on it, or if a mart checks uniqueness globally (`unique`)
instead of per tenant (`unique_per_org`).
"""

import json

import pytest
from dbt.cli.main import dbtRunner

TENANT_LAYERS = ("models/staging/", "models/marts/")


@pytest.fixture(scope="module")
def manifest(tmp_path_factory):
    target = tmp_path_factory.mktemp("dbt_target")
    result = dbtRunner().invoke(
        [
            "parse",
            "--project-dir",
            "dbt",
            "--profiles-dir",
            "ci",
            "--target-path",
            str(target),
            "--log-path",
            str(target),
            "--no-partial-parse",
            "--quiet",
        ]
    )
    assert result.success, f"dbt parse failed: {result.exception}"
    return json.loads((target / "manifest.json").read_text())


def _models(manifest):
    return {
        uid: node
        for uid, node in manifest["nodes"].items()
        if node["resource_type"] == "model"
        and node["original_file_path"].startswith(TENANT_LAYERS)
    }


def _tests_on(manifest, model_uid):
    """(test name, column) for every generic test attached to a model."""
    found = set()
    for node in manifest["nodes"].values():
        if node["resource_type"] != "test" or not node.get("test_metadata"):
            continue
        attached = node.get("attached_node") or next(
            iter(node["depends_on"]["nodes"]), None
        )
        if attached == model_uid:
            found.add((node["test_metadata"]["name"], node.get("column_name")))
    return found


def test_tenant_layers_were_found(manifest):
    # Guards the guard: if paths change and nothing matches, the tests below
    # would pass vacuously.
    assert len(_models(manifest)) >= 20


def test_every_staging_model_and_mart_declares_org_id(manifest):
    missing = [
        node["name"]
        for node in _models(manifest).values()
        if "org_id" not in node["columns"]
    ]
    assert missing == [], f"models without an org_id column documented: {missing}"


def test_every_staging_model_and_mart_tests_org_id_not_null(manifest):
    missing = [
        node["name"]
        for uid, node in _models(manifest).items()
        if ("not_null", "org_id") not in _tests_on(manifest, uid)
    ]
    assert missing == [], f"models without a not_null test on org_id: {missing}"


def test_marts_check_uniqueness_per_tenant_not_globally(manifest):
    offenders = [
        f"{node['name']}.{column}"
        for uid, node in _models(manifest).items()
        if node["original_file_path"].startswith("models/marts/")
        for name, column in _tests_on(manifest, uid)
        if name == "unique"
    ]
    assert offenders == [], (
        "marts must use unique_per_org (IDs are only unique within a charity): "
        f"{offenders}"
    )
