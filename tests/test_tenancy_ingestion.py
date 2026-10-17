"""Tenant isolation at the ingestion layer: every raw row must carry a valid
org_id, and nothing can overwrite it."""

import ast
from pathlib import Path

import pytest

from ingestion.common import tag_rows, validate_org_id

INGESTED_AT = "2026-10-17T00:00:00+00:00"


@pytest.mark.parametrize(
    "org_id", ["test_charity", "3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90", "ab"]
)
def test_valid_org_ids_are_accepted(org_id):
    assert validate_org_id(org_id) == org_id


@pytest.mark.parametrize(
    "org_id",
    [None, "", "a", "Test_Charity", "test charity", "org;drop", "-leading-dash", 42],
)
def test_invalid_org_ids_are_rejected(org_id):
    with pytest.raises(ValueError):
        validate_org_id(org_id)


def test_tag_rows_stamps_org_and_ingested_at():
    rows = tag_rows([{"id": 1}], "test_charity", {"_page": "p"}, INGESTED_AT)

    assert rows == [
        {
            "id": 1,
            "_page": "p",
            "_org_id": "test_charity",
            "_ingested_at": INGESTED_AT,
        }
    ]


def test_tag_rows_cannot_be_overwritten_by_source_data_or_tags():
    # A source record or a caller tag that happens to use the same name must
    # never be able to reassign a row to another tenant.
    rows = tag_rows(
        [{"_org_id": "other_charity"}],
        "test_charity",
        {"_org_id": "other_charity", "_ingested_at": "1999"},
        INGESTED_AT,
    )

    assert rows[0]["_org_id"] == "test_charity"
    assert rows[0]["_ingested_at"] == INGESTED_AT


def test_tag_rows_refuses_a_missing_org():
    with pytest.raises(ValueError):
        tag_rows([{"id": 1}], "", {}, INGESTED_AT)


def test_every_raw_load_in_the_codebase_passes_org_id():
    """Static guard: fails CI if any call to load_raw_to_bigquery anywhere in
    ingestion/ forgets the org_id argument. (It's also a required argument,
    so a forgotten one would fail at run time — this catches it before.)"""
    missing = []
    for path in Path("ingestion").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", getattr(node.func, "attr", None))
                == "load_raw_to_bigquery"
                and "org_id" not in {kw.arg for kw in node.keywords}
            ):
                missing.append(f"{path}:{node.lineno}")

    assert missing == [], f"load_raw_to_bigquery calls without org_id: {missing}"
