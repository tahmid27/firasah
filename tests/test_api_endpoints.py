"""Dashboard data endpoints: response shapes, and cross-tenant isolation on
every protected endpoint."""

import re
from datetime import UTC, date, datetime, timedelta

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
                "select sum(amount) as raised, count(*) as donations",
                [{"raised": 1.2 * amount, "donations": 1}],
            ),
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
                "select project_name, fundraiser_name, source",
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
                "as period, platform, max(follower_count) as followers",
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


DATE_NAMES = {"period", "day", "month_start", "insight_date", "activity_date"}
TIME_NAMES = {"send_time", "posted_at", "last", "as_of", "hour_start"}
FIXED = {
    "platform": "instagram",
    "source": "justgiving",
    "media_type": "IMAGE",
    "media_product_type": "FEED",
    "breakdown_type": "age",
    "last_run_status": "success",
    "currency_code": "GBP",
    "page_status": "Active",
    "hour": 10,
    "dow": 2,
    "band": 1,
    "hours_after_send": 1,
    "last_http_status": None,
}
COUNT_NAMES = {
    "donations",
    "posts",
    "n",
    "campaigns",
    "fundraisers",
    "emails_sent",
    "unique_opens",
    "unique_clicks",
    "total_clicks",
    "unsubscribe_count",
    "hard_bounces",
    "soft_bounces",
    "follower_count",
}
TEXT_HINTS = (
    "name",
    "title",
    "caption",
    "permalink",
    "url",
    "subject",
    "value",
    "traffic",
    "error",
    "_id",
)


def output_names(sql: str) -> list[str]:
    """Column names a generated query returns (alias, or the bare column)."""
    select = sql[len("select ") : sql.index(" from `")]
    items, depth, current = [], 0, ""
    for char in select:
        depth += char in "(["
        depth -= char in ")]"
        if char == "," and depth == 0:
            items.append(current.strip())
            current = ""
        else:
            current += char
    items.append(current.strip())
    return [item.rsplit(" as ", 1)[-1] for item in items]


def synthesise(name: str, tag: str, amount: float):
    if name in FIXED:
        return FIXED[name]
    if name in DATE_NAMES:
        return OCT
    if name in TIME_NAMES or name.endswith("_at"):
        return datetime(2026, 10, 5, 12, tzinfo=UTC)
    if name.startswith("is_"):
        return True
    if name in COUNT_NAMES:
        return int(amount)
    if any(hint in name for hint in TEXT_HINTS):
        return f"{tag} {name}"
    return amount


class FakeExecutor:
    """Stands in for BigQuery: answers only with the data of the org named in
    the query's @org_id parameter, and records every call. Uses canned rows
    where a marker matches the SQL, otherwise generates one row from the
    query's output columns."""

    def __init__(self, data_by_org, identity_by_org):
        self.data_by_org = data_by_org
        self.identity_by_org = identity_by_org
        self.calls = []

    def run(self, sql, params):
        org = {p.name: p.value for p in params}["org_id"]
        self.calls.append({"org": org, "sql": sql, "params": params})
        mart = re.search(r"\.(\w+)`", sql).group(1)
        for marker, rows in self.data_by_org.get(org, {}).get(mart, []):
            if marker in sql:
                return rows
        if org not in self.identity_by_org:
            return []
        tag, amount = self.identity_by_org[org]
        return [{name: synthesise(name, tag, amount) for name in output_names(sql)}]


@pytest.fixture
def executor():
    return FakeExecutor(
        {
            "charity_a": org_data("A-ONLY", 100.0),
            "charity_b": org_data("B-ONLY", 99999.0),
        },
        {"charity_a": ("A-ONLY", 100.0), "charity_b": ("B-ONLY", 99999.0)},
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


def fill(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "campaign123", path)


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
    response = client.get(fill(path), headers=bearer(token(user)))

    assert response.status_code == 200
    assert not [m for m in other_markers if m in response.text]
    assert all(call["org"] == own_org for call in executor.calls)


@pytest.mark.parametrize("path", protected_get_paths())
def test_another_charitys_id_in_the_request_is_ignored(client, executor, path):
    response = client.get(
        fill(path),
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
            client.get(fill(path), headers=bearer(token(USER_A)))
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
        "through": "2026-10-18",
        "raised": 300.0,
        "donations": 3,
        "average_gift": 100.0,
    }
    assert body["last_month"]["raised"] == 150.0
    assert body["last_month"]["through"] == "2026-09-30"
    assert body["last_month_to_date"]["through"] == "2026-09-18"
    assert body["last_month_to_date"]["raised"] == 120.0
    # Compared with the same days of September, not all of it
    assert body["raised_change_pct"] == 150.0
    assert body["excluded_non_gbp_donations"] == 1


def test_summary_with_no_previous_month_has_no_change_pct(client, executor):
    executor.data_by_org["charity_a"]["fct_donations"][1:3] = [
        ("select sum(amount) as raised, count(*) as donations", []),
        (
            "as period, sum(amount) as raised, count(*) as donations",
            [{"period": OCT, "raised": 50.0, "donations": 1}],
        ),
    ]

    body = get(client, "/fundraising/summary")

    assert body["last_month"] == {
        "month_start": "2026-09-01",
        "through": "2026-09-30",
        "raised": 0.0,
        "donations": 0,
        "average_gift": None,
    }
    assert body["last_month_to_date"]["raised"] == 0.0
    assert body["raised_change_pct"] is None


def test_summary_compares_the_same_days_of_last_month(client, executor):
    get(client, "/fundraising/summary")
    to_date = next(
        c for c in executor.calls if "select sum(amount) as raised" in c["sql"]
    )
    values = [p.value for p in to_date["params"] if p.type_ == "TIMESTAMP"]

    assert values == [
        datetime(2026, 9, 1, tzinfo=UTC),
        datetime(2026, 9, 19, tzinfo=UTC),
    ]


def test_summary_on_the_31st_compares_with_the_whole_shorter_month(client):
    main.app.dependency_overrides[get_today] = lambda: date(2026, 10, 31)

    body = get(client, "/fundraising/summary")

    assert body["last_month_to_date"]["through"] == "2026-09-30"


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


def test_fundraiser_leaderboard_date_range(client, executor):
    get(client, "/fundraising/fundraisers", start="2026-10-01", end="2026-10-18")
    values = [p.value for p in executor.calls[0]["params"] if p.type_ == "TIMESTAMP"]

    assert values == [
        datetime(2026, 10, 1, tzinfo=UTC),
        datetime(2026, 10, 19, tzinfo=UTC),
    ]


def test_fundraiser_leaderboard_is_all_time_without_a_range(client, executor):
    get(client, "/fundraising/fundraisers")

    assert not [p for p in executor.calls[0]["params"] if p.type_ == "TIMESTAMP"]


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
        ("/fundraising/fundraisers", {"start": "2026-05-01", "end": "2026-04-01"}),
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


# --- logic of the newer endpoints --------------------------------------------


def client_with(rules: dict[str, list], identity=None) -> TestClient:
    """A client whose fake warehouse answers charity_a's queries from `rules`
    ({mart: [(sql marker, rows), ...]})."""
    executor = FakeExecutor(
        {"charity_a": rules}, {"charity_a": identity} if identity else {}
    )
    main.app.dependency_overrides[get_executor] = lambda: executor
    return TestClient(main.app)


def test_gift_sizes_maps_range_buckets_to_labelled_bands(client):
    body = get(
        client_with(
            {
                "fct_donations": [
                    (
                        "range_bucket",
                        [
                            {"band": 0, "donations": 4, "raised": 20.0},
                            {"band": 5, "donations": 1, "raised": 500.0},
                        ],
                    )
                ]
            }
        ),
        "/fundraising/gift-sizes",
    )

    assert [b["band"] for b in body["bands"]] == [
        "£0–10",
        "£10–25",
        "£25–50",
        "£50–100",
        "£100–250",
        "£250+",
    ]
    assert body["bands"][0]["donations"] == 4
    assert body["bands"][5] == {
        "band": "£250+",
        "min_amount": 250.0,
        "max_amount": None,
        "donations": 1,
        "raised": 500.0,
    }
    assert body["bands"][2]["donations"] == 0


def test_gift_aid_is_a_quarter_of_eligible_donations(client):
    body = get(
        client_with(
            {
                "fct_donations": [
                    (
                        "is_gift_aid = @p",
                        [{"period": OCT, "raised": 80.0, "donations": 2}],
                    ),
                    ("as period", [{"period": OCT, "raised": 200.0, "donations": 8}]),
                ],
                "dim_fundraising_pages": [("estimate", [{"estimate": 12.5}])],
            }
        ),
        "/fundraising/gift-aid",
    )

    assert body["eligible_amount"] == 80.0
    assert body["claim_value"] == 20.0
    assert body["gift_aid_share_pct"] == 25.0
    assert body["justgiving_estimated_gift_aid"] == 12.5
    assert body["data"][-1] == {
        "period": "2026-10-01",
        "eligible_amount": 80.0,
        "claim_value": 20.0,
    }


def test_timing_converts_bigquery_weekdays_and_fills_the_grid(client):
    # BigQuery DAYOFWEEK 1 = Sunday; the API uses ISO (7 = Sunday)
    body = get(
        client_with(
            {
                "fct_donations": [
                    (
                        "DAYOFWEEK",
                        [{"dow": 1, "hour": 20, "donations": 3, "raised": 60.0}],
                    )
                ]
            }
        ),
        "/fundraising/timing",
    )

    assert len(body["cells"]) == 7 * 24
    sunday_8pm = [c for c in body["cells"] if c["count"]]
    assert sunday_8pm == [{"day_of_week": 7, "hour": 20, "count": 3, "value": 60.0}]


def test_targets_report_progress_highest_first(client):
    rows = [
        {
            "fundraiser_name": "half",
            "project_name": "p",
            "page_status": "Active",
            "fundraising_target": 200,
            "total_raised": 100,
        },
        {
            "fundraiser_name": "over",
            "project_name": "p",
            "page_status": "Active",
            "fundraising_target": 100,
            "total_raised": 150,
        },
    ]
    body = get(
        client_with({"dim_fundraising_pages": [("fundraising_target", rows)]}),
        "/fundraising/targets",
    )

    assert [(r["fundraiser_name"], r["progress_pct"]) for r in body["rows"]] == [
        ("over", 150.0),
        ("half", 50.0),
    ]


def test_net_followers_is_the_change_between_periods(client):
    rows = [
        {
            "period": date(2026, 9, 21),
            "platform": "instagram",
            "account_id": "a",
            "followers": 100,
        },
        {
            "period": date(2026, 9, 28),
            "platform": "instagram",
            "account_id": "a",
            "followers": 110,
        },
        {
            "period": date(2026, 10, 12),
            "platform": "instagram",
            "account_id": "a",
            "followers": 105,
        },
    ]
    body = get(
        client_with({"fct_social_account_stats": [("account_id", rows)]}),
        "/social/net-followers",
        start="2026-09-28",
        end="2026-10-18",
    )

    assert body["data"] == [
        {"period": "2026-09-28", "instagram": 10.0},
        {"period": "2026-10-05", "instagram": None},  # no reading that week
        {"period": "2026-10-12", "instagram": None},  # nothing to compare with
    ]


def test_posts_rank_by_engagement_with_unknowns_last(client):
    base = {
        "caption": "c",
        "permalink": "p",
        "share_count": 0,
        "save_count": 0,
        "comment_count": 0,
    }
    rows = [
        {
            **base,
            "post_id": "ig-low",
            "platform": "instagram",
            "posted_at": datetime(2026, 10, 1, tzinfo=UTC),
            "media_type": "IMAGE",
            "media_product_type": "FEED",
            "view_count": None,
            "reach": 100,
            "like_count": 5,
        },
        {
            **base,
            "post_id": "ig-reel",
            "platform": "instagram",
            "posted_at": datetime(2026, 10, 2, tzinfo=UTC),
            "media_type": "VIDEO",
            "media_product_type": "REELS",
            "view_count": 900,
            "reach": 100,
            "like_count": 20,
        },
        {
            **base,
            "post_id": "ig-old",
            "platform": "instagram",
            "posted_at": datetime(2017, 1, 1, tzinfo=UTC),
            "media_type": "IMAGE",
            "media_product_type": "FEED",
            "view_count": None,
            "reach": None,
            "like_count": 9,
        },
        {
            **base,
            "post_id": "tt",
            "platform": "tiktok",
            "posted_at": datetime(2026, 10, 3, tzinfo=UTC),
            "media_type": "VIDEO",
            "media_product_type": None,
            "view_count": 200,
            "reach": None,
            "like_count": 20,
        },
    ]
    body = get(client_with({"fct_social_posts": [("post_id", rows)]}), "/social/posts")

    assert [
        (r["post_id"], r["format"], r["engagement_rate"]) for r in body["rows"]
    ] == [
        ("ig-reel", "Reel", 0.2),
        ("tt", "TikTok video", 0.1),  # interactions / views for TikTok
        ("ig-low", "Image", 0.05),  # interactions / reach for Instagram
        ("ig-old", "Image", None),  # predates insights: no reach
    ]
    assert body["rows"][1]["view_to_like_rate"] == 0.1


def test_demographic_shares_are_of_classified_followers(client):
    body = get(
        client_with(
            {
                "fct_social_follower_demographics": [
                    (
                        "max(ingested_at)",
                        [{"as_of": datetime(2026, 10, 18, tzinfo=UTC)}],
                    ),
                    (
                        "breakdown_type",
                        [
                            {
                                "breakdown_type": "gender",
                                "breakdown_value": "F",
                                "follower_count": 30,
                            },
                            {
                                "breakdown_type": "gender",
                                "breakdown_value": "M",
                                "follower_count": 90,
                            },
                        ],
                    ),
                ]
            }
        ),
        "/social/demographics",
    )

    assert body["breakdowns"]["gender"] == [
        {"value": "F", "followers": 30, "share_pct": 25.0},
        {"value": "M", "followers": 90, "share_pct": 75.0},
    ]


def test_email_lift_compares_two_days_with_the_baseline(client):
    sent = datetime(2026, 10, 10, 9, tzinfo=UTC)
    daily = [
        {"day": date(2026, 10, 10) - timedelta(days=i), "raised": 10.0, "donations": 1}
        for i in range(1, 29)
    ]
    daily += [
        {"day": date(2026, 10, 10), "raised": 50.0, "donations": 3},
        {"day": date(2026, 10, 11), "raised": 30.0, "donations": 2},
    ]
    body = get(
        client_with(
            {
                "fct_mailchimp_campaigns": [
                    (
                        "campaign_id",
                        [
                            {
                                "campaign_id": "c1",
                                "campaign_title": "Appeal",
                                "send_time": sent,
                            }
                        ],
                    )
                ],
                "fct_donations": [("as day", daily)],
            }
        ),
        "/appeals/email-lift",
    )

    row = body["rows"][0]
    assert (row["raised_2_days"], row["donations_2_days"], row["typical_2_days"]) == (
        80.0,
        5,
        20.0,
    )
    assert row["lift_pct"] == 300.0


def test_window_report_compares_with_the_window_before(client):
    body = get(
        client_with({}, identity=("A-ONLY", 100.0)),
        "/appeals/window-report",
        start="2026-10-01",
        end="2026-10-10",
    )

    assert (body["current"]["start"], body["current"]["end"]) == (
        "2026-10-01",
        "2026-10-10",
    )
    assert (body["previous"]["start"], body["previous"]["end"]) == (
        "2026-09-21",
        "2026-09-30",
    )


def test_data_health_lists_every_source_even_unconnected_ones(client):
    rows = [
        {
            "source": "instagram",
            "last_data_at": datetime(2026, 10, 18, 6, tzinfo=UTC),
            "last_run_at": None,
            "last_run_status": "failed",
            "last_error_type": "HTTPStatusError",
            "last_http_status": 401,
            "last_success_at": None,
        }
    ]
    from api.data import get_now

    main.app.dependency_overrides[get_now] = lambda: datetime(
        2026, 10, 18, 12, tzinfo=UTC
    )
    body = get(
        client_with({"fct_source_status": [("source", rows)]}), "/data-health/sources"
    )

    by_source = {s["source"]: s for s in body["sources"]}
    assert list(by_source) == [
        "justgiving",
        "launchgood",
        "instagram",
        "tiktok",
        "mailchimp",
    ]
    assert by_source["instagram"]["hours_since_data"] == 6.0
    assert by_source["instagram"]["last_http_status"] == 401
    assert by_source["tiktok"]["last_data_at"] is None


def test_another_charitys_campaign_is_not_found_and_looks_like_a_missing_one(client):
    owned = {("charity_a", "a-camp"), ("charity_b", "b-camp")}

    class OwnershipExecutor:
        def run(self, sql, params):
            values = {p.name: p.value for p in params}
            if "fct_mailchimp_campaigns" in sql:
                key = (values["org_id"], values["p0"])
                return (
                    [{"campaign_id": key[1], "campaign_title": "t"}]
                    if key in owned
                    else []
                )
            return []

    main.app.dependency_overrides[get_executor] = lambda: OwnershipExecutor()
    as_a = bearer(token(USER_A))

    own = client.get("/email/campaigns/a-camp/links", headers=as_a)
    theirs = client.get("/email/campaigns/b-camp/links", headers=as_a)
    missing = client.get("/email/campaigns/no-such/links", headers=as_a)

    assert own.status_code == 200
    assert theirs.status_code == missing.status_code == 404
    assert theirs.json() == missing.json()
    assert (
        client.get(
            "/email/campaigns/b-camp/links", headers=bearer(token(USER_B))
        ).status_code
        == 200
    )


def test_campaign_ids_with_odd_characters_are_rejected(client):
    response = client.get(
        "/email/campaigns/a%20b';--/links", headers=bearer(token(USER_A))
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/fundraising/gift-sizes",
        "/fundraising/zakat",
        "/fundraising/traffic-sources",
        "/fundraising/timing",
    ],
)
def test_totals_endpoints_accept_multi_year_ranges(client, path):
    response = client.get(
        path, params={"start": "2022-01-01"}, headers=bearer(token(USER_A))
    )

    assert response.status_code == 200


def test_old_instagram_posts_get_no_reach_based_engagement_rate(client):
    from api.data import get_now

    main.app.dependency_overrides[get_now] = lambda: datetime(2026, 10, 18, tzinfo=UTC)
    base = {
        "caption": "c",
        "permalink": "p",
        "share_count": 0,
        "save_count": 0,
        "comment_count": 0,
        "view_count": None,
        "platform": "instagram",
        "media_type": "IMAGE",
        "media_product_type": "FEED",
    }
    rows = [
        # Real shape of the bug: lifetime likes, but reach only covers what's left
        {
            **base,
            "post_id": "old",
            "posted_at": datetime(2018, 7, 7, tzinfo=UTC),
            "reach": 8,
            "like_count": 68,
        },
        {
            **base,
            "post_id": "new",
            "posted_at": datetime(2026, 9, 1, tzinfo=UTC),
            "reach": 200,
            "like_count": 20,
        },
    ]
    body = get(client_with({"fct_social_posts": [("post_id", rows)]}), "/social/posts")

    rates = {r["post_id"]: r["engagement_rate"] for r in body["rows"]}
    assert rates == {"new": 0.1, "old": None}
