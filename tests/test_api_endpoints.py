"""Dashboard data endpoints: response shapes, and cross-tenant isolation on
every protected endpoint."""

import re
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import main
from api import schemas
from api.auth import get_signing_keys
from api.data import get_today
from api.settings import get_settings
from api.tenancy import get_membership_lookup
from api.warehouse import get_executor
from tests.api_helpers import (
    SETTINGS,
    USER_A,
    USER_B,
    FakeMembershipLookup,
    FakeSigningKeys,
    bearer,
    token,
)

TODAY = date(2026, 10, 18)
SEPT, OCT = date(2026, 9, 1), date(2026, 10, 1)


def org_data(tag: str, amount: float) -> dict:
    """Canned query results per mart, chosen by a marker in the SQL. Every
    value carries the org's tag so leaks are easy to spot."""
    when = datetime(2026, 10, 5, tzinfo=UTC)
    return {
        "fct_donations": [
            ("currency_code != @", [{"donations": 1}]),
            (
                "as period, sum(amount) as raised, count(*) as donations",
                [
                    {"period": OCT, "raised": 3 * amount, "donations": 3},
                    {"period": SEPT, "raised": 1.5 * amount, "donations": 2},
                ],
            ),
            (
                "as period, source, sum(amount) as raised",
                [
                    {"period": OCT, "source": "justgiving", "raised": amount},
                    {"period": SEPT, "source": "launchgood", "raised": amount / 2},
                ],
            ),
            (
                "fundraiser_name",
                [
                    {
                        "project_name": f"{tag} appeal",
                        "fundraiser_name": f"{tag} fundraiser",
                        "source": "justgiving",
                        "raised": amount,
                        "donations": 2,
                        "average_gift": amount / 2,
                        "last_donation_at": when,
                    }
                ],
            ),
        ],
        "fct_social_account_stats": [
            (
                "as followers",
                [
                    {
                        "period": date(2026, 10, 16),
                        "platform": "instagram",
                        "followers": amount,
                    },
                    {
                        "period": date(2026, 10, 18),
                        "platform": "instagram",
                        "followers": amount,
                    },
                ],
            )
        ],
        "fct_mailchimp_campaigns": [
            (
                "campaign_id",
                [
                    {
                        "campaign_id": f"{tag}-campaign",
                        "campaign_title": f"{tag} newsletter",
                        "subject_line": f"{tag} subject",
                        "send_time": when,
                        "emails_sent": int(amount),
                        "unique_opens": 50,
                        "open_rate": 0.5,
                        "unique_clicks": 10,
                        "click_rate": 0.1,
                        "unsubscribe_count": 1,
                        "hard_bounces": 2,
                        "soft_bounces": 3,
                    }
                ],
            )
        ],
    }


class FakeExecutor:
    """Stands in for BigQuery: answers only with the data of the org named in
    the query's @org_id parameter, and records every call."""

    def __init__(self, data_by_org):
        self.data_by_org = data_by_org
        self.calls = []

    def run(self, sql, params):
        org = {p.name: p.value for p in params}["org_id"]
        self.calls.append({"org": org, "sql": sql, "params": params})
        mart = re.search(r"\.(fct_\w+)`", sql).group(1)
        for marker, rows in self.data_by_org.get(org, {}).get(mart, []):
            if marker in sql:
                return rows
        return []


@pytest.fixture
def executor():
    return FakeExecutor(
        {
            "charity_a": org_data("A-ONLY", 100.0),
            "charity_b": org_data("B-ONLY", 99999.0),
        }
    )


@pytest.fixture
def client(executor):
    main.app.dependency_overrides = {
        get_settings: lambda: SETTINGS,
        get_signing_keys: lambda: FakeSigningKeys(),
        get_membership_lookup: lambda: FakeMembershipLookup(),
        get_executor: lambda: executor,
        get_today: lambda: TODAY,
    }
    yield TestClient(main.app)
    main.app.dependency_overrides = {}


def protected_get_paths():
    return sorted(
        path
        for path, operations in main.app.openapi()["paths"].items()
        if "get" in operations and path not in {"/health", "/auth/tiktok/callback"}
    )


# --- cross-tenant isolation, every endpoint -----------------------------------


@pytest.mark.parametrize("path", protected_get_paths())
@pytest.mark.parametrize(
    ("user", "own_org", "other_markers"),
    [
        (USER_A, "charity_a", ["B-ONLY", "99999", "charity_b"]),
        (USER_B, "charity_b", ["A-ONLY", "charity_a"]),
    ],
)
def test_each_charity_only_ever_sees_its_own_data(
    client, executor, path, user, own_org, other_markers
):
    response = client.get(path, headers=bearer(token(user)))

    assert response.status_code == 200
    assert not [m for m in other_markers if m in response.text]
    assert all(call["org"] == own_org for call in executor.calls)


@pytest.mark.parametrize("path", protected_get_paths())
def test_another_charitys_id_in_the_request_is_ignored(client, executor, path):
    response = client.get(
        path,
        params={"org_id": "charity_b", "org": "charity_b"},
        headers={**bearer(token(USER_A)), "X-Org-Id": "charity_b"},
    )

    assert response.status_code == 200
    assert "B-ONLY" not in response.text and "99999" not in response.text
    assert all(call["org"] == "charity_a" for call in executor.calls)


def test_data_endpoints_actually_query_the_warehouse(client, executor):
    # Guards the isolation tests above against passing on empty responses
    for path in protected_get_paths():
        if path != "/me":
            executor.calls.clear()
            client.get(path, headers=bearer(token(USER_A)))
            assert executor.calls, path


# --- shapes and maths --------------------------------------------------------


def get(client, path, **params):
    response = client.get(path, params=params, headers=bearer(token(USER_A)))
    assert response.status_code == 200, response.text
    return response.json()


def test_summary(client):
    body = get(client, "/fundraising/summary")

    assert body["currency"] == "GBP"
    assert body["this_month"] == {
        "month_start": "2026-10-01",
        "raised": 300.0,
        "donations": 3,
        "average_gift": 100.0,
    }
    assert body["last_month"]["raised"] == 150.0
    assert body["raised_change_pct"] == 100.0
    assert body["excluded_non_gbp_donations"] == 1


def test_summary_with_no_previous_month_has_no_change_pct(client, executor):
    executor.data_by_org["charity_a"]["fct_donations"][1] = (
        "as period, sum(amount) as raised, count(*) as donations",
        [{"period": OCT, "raised": 50.0, "donations": 1}],
    )

    body = get(client, "/fundraising/summary")

    assert body["last_month"] == {
        "month_start": "2026-09-01",
        "raised": 0.0,
        "donations": 0,
        "average_gift": None,
    }
    assert body["raised_change_pct"] is None


def test_summary_only_sums_gbp(client, executor):
    get(client, "/fundraising/summary")
    totals = next(c for c in executor.calls if "sum(amount)" in c["sql"])

    assert "currency_code = @p0" in totals["sql"]
    assert {p.name: p.value for p in totals["params"]}["p0"] == "GBP"


def test_income_over_time_is_recharts_shaped_with_gaps_filled(client):
    body = get(client, "/fundraising/income-over-time")

    assert body["unit"] == "GBP"
    assert body["series"] == [
        {"key": "justgiving", "label": "JustGiving"},
        {"key": "launchgood", "label": "LaunchGood"},
    ]
    assert len(body["data"]) == 12  # Nov 2025 to Oct 2026
    assert body["data"][0] == {
        "period": "2025-11-01",
        "justgiving": 0.0,
        "launchgood": 0.0,
    }
    assert body["data"][-2] == {
        "period": "2026-09-01",
        "justgiving": 0.0,
        "launchgood": 50.0,
    }
    assert body["data"][-1] == {
        "period": "2026-10-01",
        "justgiving": 100.0,
        "launchgood": 0.0,
    }


def test_income_over_time_filters_timestamps_with_timestamps(client, executor):
    get(client, "/fundraising/income-over-time", start="2026-01-01", end="2026-03-31")
    params = {p.name: p for p in executor.calls[0]["params"]}

    assert params["p1"].type_ == "TIMESTAMP"
    assert params["p1"].value == datetime(2026, 1, 1, tzinfo=UTC)
    assert params["p2"].value == datetime(2026, 4, 1, tzinfo=UTC)


def test_followers_over_time_leaves_missing_days_empty(client):
    body = get(
        client, "/social/followers-over-time", start="2026-10-16", end="2026-10-18"
    )

    assert body["unit"] == "followers"
    assert body["data"] == [
        {"period": "2026-10-16", "instagram": 100.0},
        {"period": "2026-10-17", "instagram": None},
        {"period": "2026-10-18", "instagram": 100.0},
    ]


def test_fundraiser_leaderboard(client, executor):
    body = get(client, "/fundraising/fundraisers", project="A-ONLY appeal")

    assert body["rows"][0]["fundraiser_name"] == "A-ONLY fundraiser"
    assert body["rows"][0]["average_gift"] == 50.0
    sql = executor.calls[0]["sql"]
    assert "A-ONLY appeal" not in sql
    assert "order by raised desc limit 50" in sql


def test_campaign_scorecard(client):
    row = get(client, "/email/campaigns")["rows"][0]

    assert row["click_to_open_rate"] == 0.2
    assert row["bounces"] == 5


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/fundraising/income-over-time", {"interval": "year"}),
        ("/fundraising/income-over-time", {"start": "2026-05-01", "end": "2026-04-01"}),
        ("/social/followers-over-time", {"start": "2024-01-01", "end": "2026-10-18"}),
        ("/fundraising/fundraisers", {"limit": 0}),
        ("/fundraising/fundraisers", {"limit": 201}),
        ("/fundraising/fundraisers", {"project": "x" * 201}),
        ("/email/campaigns", {"limit": 500}),
    ],
)
def test_bad_parameters_are_rejected(client, path, params):
    response = client.get(path, params=params, headers=bearer(token(USER_A)))

    assert response.status_code == 422


def test_no_response_model_has_a_credential_shaped_field():
    suspicious = re.compile(r"token|secret|password|api_?key|credential", re.IGNORECASE)
    models = [
        obj
        for obj in vars(schemas).values()
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel
    ]

    assert models
    assert [
        f"{model.__name__}.{field}"
        for model in models
        for field in model.model_fields
        if suspicious.search(field)
    ] == []
