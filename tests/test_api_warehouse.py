"""The BigQuery query helper: every query is forced onto the caller's charity,
values travel only as parameters, and names come only from the allowlist."""

from datetime import date

import pytest

from api.settings import Settings
from api.tenancy import OrgContext
from api.warehouse import MARTS, Filter, build_query, query_mart
from tests.api_helpers import SETTINGS

CTX_A = OrgContext(user_id="u", org_id="charity_a", role="admin")


def params_by_name(params):
    return {p.name: p.value for p in params}


def test_every_query_is_filtered_to_the_callers_charity():
    sql, params = build_query(SETTINGS, CTX_A, "fct_donations", ["amount"])

    assert "where org_id = @org_id" in sql
    assert params_by_name(params) == {"org_id": "charity_a"}
    assert sql.startswith(
        "select amount from `test-project.test_dataset.fct_donations`"
    )


def test_the_tenant_filter_survives_extra_filters_and_sorting():
    sql, params = build_query(
        SETTINGS,
        CTX_A,
        "fct_donations",
        ["donation_date", "amount"],
        filters=[Filter("donation_date", ">=", date(2026, 1, 1))],
        order_by=[("donation_date", "desc")],
        limit=50,
    )

    assert sql.endswith(
        "where org_id = @org_id and donation_date >= @p0"
        " order by donation_date desc limit 50"
    )
    assert params_by_name(params) == {"org_id": "charity_a", "p0": date(2026, 1, 1)}


def test_values_never_enter_the_sql_text():
    attack = "x' or '1'='1"
    sql, params = build_query(
        SETTINGS,
        CTX_A,
        "fct_donations",
        ["amount"],
        filters=[Filter("fundraiser_name", "=", attack)],
    )

    assert attack not in sql
    assert params_by_name(params)["p0"] == attack


@pytest.mark.parametrize(
    ("description", "kwargs"),
    [
        ("unknown mart", {"mart": "raw_justgiving_donations", "columns": ["id"]}),
        ("unknown column", {"mart": "fct_donations", "columns": ["donor_email"]}),
        ("selecting org_id", {"mart": "fct_donations", "columns": ["org_id"]}),
        (
            "SQL in a column name",
            {"mart": "fct_donations", "columns": ["amount; drop"]},
        ),
        ("no columns", {"mart": "fct_donations", "columns": []}),
        (
            "filtering on org_id to reach another charity",
            {
                "mart": "fct_donations",
                "columns": ["amount"],
                "filters": [Filter("org_id", "=", "charity_b")],
            },
        ),
        (
            "an operator outside the allowlist",
            {
                "mart": "fct_donations",
                "columns": ["amount"],
                "filters": [Filter("amount", "or 1=1 or", 0)],
            },
        ),
        (
            "a sort direction that is really SQL",
            {
                "mart": "fct_donations",
                "columns": ["amount"],
                "order_by": [("amount", "desc; drop table x")],
            },
        ),
        (
            "a limit too big",
            {"mart": "fct_donations", "columns": ["amount"], "limit": 10**7},
        ),
        ("a zero limit", {"mart": "fct_donations", "columns": ["amount"], "limit": 0}),
    ],
)
def test_unsafe_requests_are_rejected(description, kwargs):
    with pytest.raises(ValueError):
        build_query(SETTINGS, CTX_A, **kwargs)


def test_org_id_is_never_on_the_allowlist():
    assert all("org_id" not in columns for columns in MARTS.values())


def test_a_malformed_org_in_the_context_is_rejected():
    bad = OrgContext(user_id="u", org_id="charity_a' or 'x", role="admin")
    with pytest.raises(ValueError):
        build_query(SETTINGS, bad, "fct_donations", ["amount"])


def test_unsafe_bigquery_project_or_dataset_names_are_rejected():
    with pytest.raises(ValueError):
        Settings("https://x.supabase.co", "k", "proj`; drop", "firasah_dev")


def test_query_mart_hands_the_executor_the_callers_org():
    class RecordingExecutor:
        def run(self, sql, params):
            self.sql, self.params = sql, params
            return [{"amount": 10}]

    executor = RecordingExecutor()
    rows = query_mart(
        CTX_A, "fct_donations", ["amount"], executor=executor, settings=SETTINGS
    )

    assert rows == [{"amount": 10}]
    assert params_by_name(executor.params)["org_id"] == "charity_a"
