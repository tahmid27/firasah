"""The only path from the API to BigQuery; every query is scoped to the caller's org."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Protocol

from fastapi import Depends
from google.cloud import bigquery

from api.settings import Settings, get_settings
from api.tenancy import OrgContext
from core.org_ids import validate_org_id

# Columns the API may read, per mart. org_id is excluded: the helper filters on it.
MARTS: dict[str, frozenset[str]] = {
    "fct_donations": frozenset(
        {
            "donation_id",
            "source",
            "donation_date",
            "amount",
            "currency_code",
            "donor_name",
            "is_anonymous",
            "fundraiser_name",
            "project_name",
            "traffic_source",
            "is_online",
            "is_gift_aid",
            "is_zakat",
            "zakat_amount",
            "processing_fees",
            "net_amount",
            "settlement_currency",
            "has_marketing_consent",
        }
    ),
    "fct_social_posts": frozenset(
        {
            "post_id",
            "platform",
            "posted_at",
            "caption",
            "media_type",
            "media_product_type",
            "permalink",
            "view_count",
            "like_count",
            "comment_count",
            "share_count",
            "save_count",
            "reach",
            "repost_count",
            "profile_visits",
            "new_follower_count",
            "avg_watch_time_seconds",
            "skip_rate",
        }
    ),
    "fct_social_account_stats": frozenset(
        {
            "account_id",
            "platform",
            "display_name",
            "follower_count",
            "following_count",
            "post_count",
            "total_likes",
            "ingested_at",
        }
    ),
    "fct_social_account_daily": frozenset(
        {
            "account_id",
            "platform",
            "insight_date",
            "reach",
            "view_count",
            "accounts_engaged",
            "like_count",
            "comment_count",
            "share_count",
            "save_count",
            "repost_count",
            "total_interactions",
            "profile_links_taps",
        }
    ),
    "fct_social_follower_demographics": frozenset(
        {
            "account_id",
            "platform",
            "breakdown_type",
            "breakdown_value",
            "follower_count",
            "ingested_at",
        }
    ),
    "fct_mailchimp_campaigns": frozenset(
        {
            "campaign_id",
            "campaign_title",
            "subject_line",
            "campaign_type",
            "send_time",
            "list_id",
            "list_name",
            "emails_sent",
            "opens_total",
            "unique_opens",
            "open_rate",
            "clicks_total",
            "unique_clicks",
            "click_rate",
            "hard_bounces",
            "soft_bounces",
            "unsubscribe_count",
            "abuse_reports",
        }
    ),
    "fct_mailchimp_link_clicks": frozenset(
        {
            "campaign_id",
            "link_id",
            "url",
            "total_clicks",
            "unique_clicks",
            "click_percentage",
            "unique_click_percentage",
            "last_clicked_at",
        }
    ),
    "fct_mailchimp_audience_stats": frozenset(
        {
            "list_id",
            "list_name",
            "member_count",
            "unsubscribe_count",
            "campaign_count",
            "avg_open_rate",
            "avg_click_rate",
            "ingested_at",
        }
    ),
    "fct_mailchimp_audience_daily": frozenset(
        {
            "list_id",
            "activity_date",
            "new_subscribers",
            "unsubscribes",
            "net_subscribers",
            "emails_sent",
            "unique_opens",
            "recipient_clicks",
            "hard_bounces",
            "soft_bounces",
        }
    ),
    "fct_mailchimp_audience_monthly": frozenset(
        {
            "list_id",
            "month_start",
            "existing_subscribers",
            "imported_subscribers",
            "opt_in_subscribers",
            "subscribed",
            "unsubscribed",
            "cleaned",
            "pending",
        }
    ),
}

OPERATORS = frozenset({"=", "!=", "<", "<=", ">", ">="})
MAX_LIMIT = 10_000


@dataclass(frozen=True)
class Filter:
    column: str
    op: str
    value: Any


class QueryExecutor(Protocol):
    def run(
        self, sql: str, params: list[bigquery.ScalarQueryParameter]
    ) -> list[dict]: ...


class BigQueryExecutor:
    def __init__(self, project: str):
        self._client = bigquery.Client(project=project)

    def run(self, sql, params):
        job = self._client.query(
            sql, job_config=bigquery.QueryJobConfig(query_parameters=params)
        )
        return [dict(row) for row in job.result()]


_executors: dict[str, BigQueryExecutor] = {}


def get_executor(settings: Annotated[Settings, Depends(get_settings)]) -> QueryExecutor:
    if settings.bigquery_project not in _executors:
        _executors[settings.bigquery_project] = BigQueryExecutor(
            settings.bigquery_project
        )
    return _executors[settings.bigquery_project]


def _param(name: str, value: Any) -> bigquery.ScalarQueryParameter:
    # bool before int: True is also an int
    for python_type, bq_type in (
        (bool, "BOOL"),
        (int, "INT64"),
        (float, "FLOAT64"),
        (Decimal, "NUMERIC"),
        (datetime, "TIMESTAMP"),
        (date, "DATE"),
        (str, "STRING"),
    ):
        if isinstance(value, python_type):
            return bigquery.ScalarQueryParameter(name, bq_type, value)
    raise ValueError(f"unsupported filter value type: {type(value).__name__}")


def _check_column(mart: str, column: str) -> str:
    if column not in MARTS[mart]:
        raise ValueError(f"column {column!r} is not allowed on {mart}")
    return column


def build_query(
    settings: Settings,
    ctx: OrgContext,
    mart: str,
    columns: Sequence[str],
    *,
    filters: Sequence[Filter] = (),
    order_by: Sequence[tuple[str, str]] = (),
    limit: int | None = None,
) -> tuple[str, list[bigquery.ScalarQueryParameter]]:
    """Returns (sql, parameters) without running anything."""
    if mart not in MARTS:
        raise ValueError(f"unknown mart: {mart!r}")
    if not columns:
        raise ValueError("at least one column is required")

    select = ", ".join(_check_column(mart, c) for c in columns)
    table = f"`{settings.bigquery_project}.{settings.bigquery_dataset}.{mart}`"

    where = ["org_id = @org_id"]
    params = [_param("org_id", validate_org_id(ctx.org_id))]

    for i, f in enumerate(filters):
        if f.op not in OPERATORS:
            raise ValueError(f"operator {f.op!r} is not allowed")
        name = f"p{i}"
        where.append(f"{_check_column(mart, f.column)} {f.op} @{name}")
        params.append(_param(name, f.value))

    sql = f"select {select} from {table} where {' and '.join(where)}"

    if order_by:
        parts = []
        for column, direction in order_by:
            if direction.lower() not in ("asc", "desc"):
                raise ValueError(f"sort direction {direction!r} is not allowed")
            parts.append(f"{_check_column(mart, column)} {direction.lower()}")
        sql += " order by " + ", ".join(parts)

    if limit is not None:
        if not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
        sql += f" limit {limit}"

    return sql, params


def query_mart(
    ctx: OrgContext,
    mart: str,
    columns: Sequence[str],
    *,
    executor: QueryExecutor,
    settings: Settings,
    filters: Sequence[Filter] = (),
    order_by: Sequence[tuple[str, str]] = (),
    limit: int | None = None,
) -> list[dict]:
    """Rows from one mart, for the caller's charity only."""
    sql, params = build_query(
        settings,
        ctx,
        mart,
        columns,
        filters=filters,
        order_by=order_by,
        limit=limit,
    )
    return executor.run(sql, params)
