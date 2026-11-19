"""The synthetic reload must never touch real data, and a nightly refresh must
leave the dashboard tables in place until dbt rebuilds them."""

from types import SimpleNamespace

import pytest

from synthetic.load import reset_dataset, tables_to_delete

TABLES = [
    "raw_justgiving_donations",
    "stg_justgiving_donations",
    "justgiving_donations_snapshot",
    "int_donations_unioned",
    "fct_donations",
    "dim_fundraising_pages",
    "fct_social_posts",
]


class FakeClient:
    project = "p"

    def __init__(self, tables=TABLES, dataset_exists=True):
        self.tables = list(tables)
        self.dataset_exists = dataset_exists
        self.deleted: list[str] = []
        self.created = False

    def get_dataset(self, ref):
        if not self.dataset_exists:
            from google.api_core.exceptions import NotFound

            raise NotFound("missing")

    def create_dataset(self, dataset):
        self.created = True

    def list_tables(self, ref):
        return [
            SimpleNamespace(table_id=t, reference=f"{ref}.{t}") for t in self.tables
        ]

    def delete_table(self, reference):
        self.deleted.append(reference.rsplit(".", 1)[1])


def test_full_reset_deletes_everything():
    client = FakeClient()
    reset_dataset(client, "firasah_synthetic")
    assert sorted(client.deleted) == sorted(TABLES)


def test_keep_marts_leaves_only_dashboard_tables():
    client = FakeClient()
    reset_dataset(client, "firasah_synthetic", keep_marts=True)
    assert "fct_donations" not in client.deleted
    assert "dim_fundraising_pages" not in client.deleted
    assert "fct_social_posts" not in client.deleted
    # Raw data, staging views and the snapshot are all rebuilt from scratch
    for name in (
        "raw_justgiving_donations",
        "stg_justgiving_donations",
        "justgiving_donations_snapshot",
        "int_donations_unioned",
    ):
        assert name in client.deleted


def test_refuses_a_dataset_that_is_not_synthetic():
    client = FakeClient()
    with pytest.raises(SystemExit):
        reset_dataset(client, "firasah_dev", keep_marts=True)
    assert client.deleted == []


def test_existing_dataset_is_not_recreated():
    # Recreating a dataset would drop its access grants (the API's read access)
    client = FakeClient()
    reset_dataset(client, "firasah_synthetic")
    assert client.created is False


def test_missing_dataset_is_created():
    client = FakeClient(tables=[], dataset_exists=False)
    reset_dataset(client, "firasah_synthetic")
    assert client.created is True


def test_tables_to_delete_without_keep_returns_all():
    assert tables_to_delete(["fct_x", "raw_y"], keep_marts=False) == ["fct_x", "raw_y"]
