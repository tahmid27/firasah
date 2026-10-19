"""Appeals endpoints: donations, posts, emails and followers on one timeline."""

from collections import defaultdict
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from api.data import Today, Warehouse
from api.periods import periods, start_of_day
from api.routes.common import (
    check_range,
    latest_total,
    money,
    optional_range,
    pct_change,
)
from api.schemas import (
    AppealTimeline,
    EmailLift,
    EmailLiftRow,
    SeriesInfo,
    TimelineEvent,
    TimeSeriesResponse,
    WindowReport,
    WindowStats,
)
from api.warehouse import MAX_LIMIT, Agg, Bucket, Filter

router = APIRouter(prefix="/appeals", tags=["appeals"])

GBP = Filter("currency_code", "=", "GBP")
CAPTION_LENGTH = 120


def _between(column: str, start: date, end: date) -> list[Filter]:
    return [
        Filter(column, ">=", start_of_day(start)),
        Filter(column, "<", start_of_day(end + timedelta(days=1))),
    ]


def _daily_donations(
    wh: Warehouse, start: date, end: date, interval: str = "day"
) -> dict[date, dict]:
    rows = wh.fetch(
        "fct_donations",
        [
            Bucket("donation_date", interval, "day"),
            Agg("sum", "amount", "raised"),
            Agg("count", "*", "donations"),
        ],
        filters=[GBP, *_between("donation_date", start, end)],
    )
    return {row["day"]: row for row in rows}


@router.get("/timeline", response_model=AppealTimeline)
def timeline(
    wh: Warehouse,
    today: Today,
    start: date | None = None,
    end: date | None = None,
    interval: Literal["day", "week"] = "day",
):
    """Donations per day (or week) with every post and email as an event."""
    end = end or today
    start = start or end - timedelta(days=89)
    check_range(start, end, interval)
    daily = _daily_donations(wh, start, end, interval)
    # Newest first, so if the cap is ever reached it's the oldest that drop
    posts = wh.fetch(
        "fct_social_posts",
        ["posted_at", "platform", "caption", "permalink"],
        filters=_between("posted_at", start, end),
        order_by=[("posted_at", "desc")],
        limit=MAX_LIMIT,
    )
    emails = wh.fetch(
        "fct_mailchimp_campaigns",
        ["send_time", "campaign_title"],
        filters=_between("send_time", start, end),
        order_by=[("send_time", "desc")],
        limit=MAX_LIMIT,
    )
    events = [
        TimelineEvent(
            at=p["posted_at"],
            kind="post",
            platform=p["platform"],
            title=(p["caption"] or "")[:CAPTION_LENGTH] or None,
            link=p["permalink"],
        )
        for p in posts
    ] + [
        TimelineEvent(
            at=e["send_time"],
            kind="email",
            platform="mailchimp",
            title=e["campaign_title"],
            link=None,
        )
        for e in emails
    ]
    return AppealTimeline(
        donations=TimeSeriesResponse(
            interval=interval,
            start=start,
            end=end,
            unit="GBP",
            series=[SeriesInfo(key="raised", label="Raised")],
            data=[
                {"period": d, "raised": money(daily.get(d, {}).get("raised"))}
                for d in periods(start, end, interval)
            ],
        ),
        events=sorted(events, key=lambda e: e.at),
    )


def _window(wh: Warehouse, start: date, end: date) -> WindowStats:
    daily = _daily_donations(wh, start, end)
    posts = wh.fetch(
        "fct_social_posts",
        [Agg("count", "*", "n")],
        filters=_between("posted_at", start, end),
    )
    emails = wh.fetch(
        "fct_mailchimp_campaigns",
        [Agg("count", "*", "n")],
        filters=_between("send_time", start, end),
    )
    followers = wh.fetch(
        "fct_social_account_stats",
        [
            Bucket("ingested_at", "day", "day"),
            "account_id",
            Agg("max", "follower_count", "f"),
        ],
        filters=[Filter("ingested_at", "<", start_of_day(end + timedelta(days=1)))],
    )
    readings: dict = defaultdict(list)
    for row in sorted(followers, key=lambda r: r["day"]):
        readings[row["account_id"]].append((row["day"], float(row["f"])))
    at_end = latest_total(dict(readings), on_or_before=end)
    at_start = latest_total(dict(readings), on_or_before=start)
    return WindowStats(
        start=start,
        end=end,
        raised=money(sum(float(r["raised"]) for r in daily.values())),
        donations=sum(int(r["donations"]) for r in daily.values()),
        posts=int(posts[0]["n"]) if posts else 0,
        emails=int(emails[0]["n"]) if emails else 0,
        follower_change=None
        if at_end is None or at_start is None
        else at_end - at_start,
    )


@router.get("/window-report", response_model=WindowReport)
def window_report(
    wh: Warehouse, today: Today, start: date | None = None, end: date | None = None
):
    """A chosen window (e.g. Ramadan) against the same-length window before it."""
    end = end or today
    start = start or end - timedelta(days=29)
    check_range(start, end, "month")  # totals, not a daily series
    length = (end - start).days + 1
    current = _window(wh, start, end)
    previous = _window(wh, start - timedelta(days=length), start - timedelta(days=1))
    return WindowReport(
        currency="GBP",
        current=current,
        previous=previous,
        raised_change_pct=pct_change(current.raised, previous.raised),
    )


@router.get("/email-lift", response_model=EmailLift)
def email_lift(
    wh: Warehouse,
    baseline_days: Annotated[int, Query(ge=7, le=180)] = 28,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    start: date | None = None,
    end: date | None = None,
):
    """Donations on the day of each email and the day after, against a typical
    two days in the weeks before it. A pattern to look at, not proof the
    email caused the donations. Newest campaigns first; only those sent in the
    range when one is given."""
    campaigns = wh.fetch(
        "fct_mailchimp_campaigns",
        ["campaign_id", "campaign_title", "send_time"],
        filters=[
            Filter("send_time", ">=", start_of_day(date(2000, 1, 1))),
            *optional_range("send_time", start, end),
        ],
        order_by=[("send_time", "desc")],
        limit=limit,
    )
    if not campaigns:
        return EmailLift(currency="GBP", baseline_days=baseline_days, rows=[])
    first = min(c["send_time"].date() for c in campaigns) - timedelta(
        days=baseline_days
    )
    last = max(c["send_time"].date() for c in campaigns) + timedelta(days=1)
    daily = _daily_donations(wh, first, last)

    def raised(day):
        return float(daily.get(day, {}).get("raised") or 0)

    rows = []
    for c in campaigns:
        sent = c["send_time"].date()
        two_days = [sent, sent + timedelta(days=1)]
        baseline = [sent - timedelta(days=i) for i in range(1, baseline_days + 1)]
        typical = sum(raised(d) for d in baseline) / baseline_days * 2
        actual = sum(raised(d) for d in two_days)
        rows.append(
            EmailLiftRow(
                campaign_id=c["campaign_id"],
                campaign_title=c["campaign_title"],
                send_time=c["send_time"],
                raised_2_days=money(actual),
                donations_2_days=sum(
                    int(daily.get(d, {}).get("donations") or 0) for d in two_days
                ),
                typical_2_days=money(typical),
                lift_pct=pct_change(actual, typical),
            )
        )
    return EmailLift(currency="GBP", baseline_days=baseline_days, rows=rows)
