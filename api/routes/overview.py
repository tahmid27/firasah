"""Overview page and data-health endpoints."""

from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter

from api.data import Now, Today, Warehouse
from api.periods import start_of_day
from api.routes.common import LABELS, SOURCES, latest_total, pct_change
from api.schemas import (
    DataHealth,
    MetricChange,
    OverviewSummary,
    SourceStatus,
    TrendPoint,
)
from api.warehouse import Agg, Bucket, Filter

router = APIRouter(tags=["overview"])

COMPARE_DAYS = 30
TREND_DAYS = 90
# Extra history before the trend starts, so its first days can carry an
# earlier reading forward
LOOKBACK_DAYS = TREND_DAYS + 30


def _readings(rows, key: str, value: str) -> dict[str, list[tuple]]:
    readings = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["day"]):
        readings[row[key]].append((row["day"], float(row[value])))
    return dict(readings)


def _metric(readings: dict[str, list[tuple]], today, compare_date) -> MetricChange:
    now = latest_total(readings)
    then = latest_total(readings, on_or_before=compare_date)
    days = [today - timedelta(days=n) for n in range(TREND_DAYS - 1, -1, -1)]
    return MetricChange(
        value=now,
        previous=then,
        change=None if now is None or then is None else now - then,
        change_pct=pct_change(now, then),
        trend=[
            TrendPoint(day=day, value=latest_total(readings, on_or_before=day))
            for day in days
        ],
    )


@router.get("/overview/summary", response_model=OverviewSummary)
def overview_summary(wh: Warehouse, today: Today):
    compare_date = today - timedelta(days=COMPARE_DAYS)
    since = [
        Filter("ingested_at", ">=", start_of_day(today - timedelta(days=LOOKBACK_DAYS)))
    ]

    followers = wh.fetch(
        "fct_social_account_stats",
        [
            Bucket("ingested_at", "day", "day"),
            "account_id",
            Agg("max", "follower_count", "followers"),
        ],
        filters=since,
    )
    subscribers = wh.fetch(
        "fct_mailchimp_audience_stats",
        [
            Bucket("ingested_at", "day", "day"),
            "list_id",
            Agg("max", "member_count", "members"),
        ],
        filters=since,
    )
    return OverviewSummary(
        followers=_metric(
            _readings(followers, "account_id", "followers"), today, compare_date
        ),
        email_subscribers=_metric(
            _readings(subscribers, "list_id", "members"), today, compare_date
        ),
        compared_with=compare_date,
    )


@router.get("/data-health/sources", response_model=DataHealth)
def data_health(wh: Warehouse, now: Now):
    rows = wh.fetch(
        "fct_source_status",
        [
            "source",
            "last_data_at",
            "last_run_at",
            "last_run_status",
            "last_error_type",
            "last_http_status",
            "last_success_at",
        ],
    )
    by_source = {row["source"]: row for row in rows}
    sources = []
    for source in SOURCES:
        row = by_source.get(source, {})
        last_data_at = row.get("last_data_at")
        sources.append(
            SourceStatus(
                source=source,
                label=LABELS[source],
                last_data_at=last_data_at,
                last_run_at=row.get("last_run_at"),
                last_run_status=row.get("last_run_status"),
                last_error_type=row.get("last_error_type"),
                last_http_status=row.get("last_http_status"),
                last_success_at=row.get("last_success_at"),
                hours_since_data=(
                    round((now - last_data_at).total_seconds() / 3600, 1)
                    if last_data_at
                    else None
                ),
            )
        )
    return DataHealth(sources=sources)
