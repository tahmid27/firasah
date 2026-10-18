"""Social endpoints (fct_social_*)."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from itertools import pairwise
from statistics import mean, median
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from api.data import Now, Today, Warehouse
from api.periods import period_start, periods, start_of_day
from api.routes.common import LABELS, check_range
from api.schemas import (
    DemographicBucket,
    Demographics,
    FormatRow,
    Formats,
    Heatmap,
    HeatmapCell,
    LastPost,
    PostingConsistency,
    PostRow,
    Posts,
    SeriesInfo,
    TimeSeriesResponse,
)
from api.warehouse import MAX_LIMIT, TIMEZONE, Agg, Bucket, Filter

router = APIRouter(prefix="/social", tags=["social"])


@router.get("/followers-over-time", response_model=TimeSeriesResponse)
def followers_over_time(
    wh: Warehouse,
    today: Today,
    interval: Literal["day", "week", "month"] = "day",
    start: date | None = None,
    end: date | None = None,
):
    end = end or today
    start = start or end - timedelta(days=89)
    check_range(start, end, interval)

    rows = wh.fetch(
        "fct_social_account_stats",
        [
            Bucket("ingested_at", interval, "period"),
            "platform",
            # Highest reading in the period; right while each platform has
            # one account per charity
            Agg("max", "follower_count", "followers"),
        ],
        filters=[
            Filter("ingested_at", ">=", start_of_day(start)),
            Filter("ingested_at", "<", start_of_day(end + timedelta(days=1))),
        ],
    )
    platforms = sorted({row["platform"] for row in rows})
    followers = {(row["period"], row["platform"]): row["followers"] for row in rows}
    # Missing periods are None (no reading), not 0
    data = [
        {"period": p, **{name: followers.get((p, name)) for name in platforms}}
        for p in periods(start, end, interval)
    ]
    return TimeSeriesResponse(
        interval=interval,
        start=start,
        end=end,
        unit="followers",
        series=[
            SeriesInfo(key=name, label=LABELS.get(name, name)) for name in platforms
        ],
        data=data,
    )


Platform = Literal["instagram", "tiktok"]
Interval = Literal["day", "week", "month"]

POST_COLUMNS = [
    "post_id",
    "platform",
    "posted_at",
    "caption",
    "media_type",
    "media_product_type",
    "permalink",
    "view_count",
    "reach",
    "like_count",
    "comment_count",
    "share_count",
    "save_count",
]
ENGAGEMENT_BASIS = (
    "likes + comments + shares + saves, divided by reach (Instagram) or views "
    "(TikTok). Not given for Instagram posts over 2 years old: Instagram keeps "
    "insights for 2 years, so their reach no longer matches their lifetime likes."
)
INSIGHTS_RETENTION = timedelta(days=730)


def _format(row: dict) -> str:
    if row["platform"] == "tiktok":
        return "TikTok video"
    if row["media_product_type"] == "REELS":
        return "Reel"
    return {"CAROUSEL_ALBUM": "Carousel", "IMAGE": "Image", "VIDEO": "Video"}.get(
        row["media_type"], row["media_type"] or "Post"
    )


def _post(row: dict, now: datetime) -> PostRow:
    interactions = sum(
        row[k] or 0
        for k in ("like_count", "comment_count", "share_count", "save_count")
    )
    if row["platform"] == "instagram":
        recent = now - row["posted_at"] <= INSIGHTS_RETENTION
        seen_by = row["reach"] if recent else None
    else:
        seen_by = row["view_count"]
    views = row["view_count"]
    return PostRow(
        post_id=row["post_id"],
        platform=row["platform"],
        posted_at=row["posted_at"],
        format=_format(row),
        caption=row["caption"],
        permalink=row["permalink"],
        views=views,
        reach=row["reach"],
        likes=row["like_count"],
        comments=row["comment_count"],
        shares=row["share_count"],
        saves=row["save_count"],
        engagement_rate=round(interactions / seen_by, 4) if seen_by else None,
        view_to_like_rate=round((row["like_count"] or 0) / views, 4) if views else None,
    )


def _all_posts(wh: Warehouse, platform: str | None, now: datetime) -> list[PostRow]:
    filters = [Filter("platform", "=", platform)] if platform else []
    rows = wh.fetch(
        "fct_social_posts",
        POST_COLUMNS,
        filters=filters,
        order_by=[("posted_at", "desc")],
        limit=MAX_LIMIT,
    )
    return [_post(row, now) for row in rows]


@router.get("/net-followers", response_model=TimeSeriesResponse)
def net_followers(
    wh: Warehouse,
    today: Today,
    interval: Literal["week", "month"] = "week",
    start: date | None = None,
    end: date | None = None,
):
    """Followers gained or lost per period, from the last reading in each period."""
    end = end or today
    start = start or end - timedelta(weeks=12)
    check_range(start, end, interval)
    lead_in = period_start(start, interval) - timedelta(days=1)
    rows = wh.fetch(
        "fct_social_account_stats",
        [
            Bucket("ingested_at", interval, "period"),
            "platform",
            "account_id",
            Agg("max", "follower_count", "followers"),
        ],
        filters=[
            Filter("ingested_at", ">=", start_of_day(period_start(lead_in, interval))),
            Filter("ingested_at", "<", start_of_day(end + timedelta(days=1))),
        ],
    )
    totals: dict = defaultdict(float)
    for row in rows:
        totals[(row["period"], row["platform"])] += float(row["followers"])
    platforms = sorted({row["platform"] for row in rows})
    all_periods = [period_start(lead_in, interval), *periods(start, end, interval)]
    data = []
    for previous, current in pairwise(all_periods):
        point = {"period": current}
        for name in platforms:
            now, before = totals.get((current, name)), totals.get((previous, name))
            point[name] = None if now is None or before is None else now - before
        data.append(point)
    return TimeSeriesResponse(
        interval=interval,
        start=start,
        end=end,
        unit="followers",
        series=[SeriesInfo(key=n, label=LABELS.get(n, n)) for n in platforms],
        data=data,
    )


@router.get("/posts", response_model=Posts)
def posts(
    wh: Warehouse,
    now: Now,
    platform: Platform | None = None,
    sort: Literal["engagement_rate", "reach", "views", "likes", "posted_at"] = (
        "engagement_rate"
    ),
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    rows = _all_posts(wh, platform, now)
    if sort != "posted_at":
        known = [r for r in rows if getattr(r, sort) is not None]
        unknown = [r for r in rows if getattr(r, sort) is None]
        # Highest first; posts without that metric go last
        rows = sorted(known, key=lambda r: getattr(r, sort), reverse=True) + unknown
    return Posts(engagement_basis=ENGAGEMENT_BASIS, rows=rows[:limit])


@router.get("/formats", response_model=Formats)
def formats(wh: Warehouse, now: Now, platform: Platform | None = None):
    """How each format performs: Reel vs image vs carousel vs TikTok video."""
    groups: dict = defaultdict(list)
    for post in _all_posts(wh, platform, now):
        groups[(post.platform, post.format)].append(post.engagement_rate)
    result = []
    for (name, fmt), rates in groups.items():
        known = [r for r in rates if r is not None]
        result.append(
            FormatRow(
                platform=name,
                format=fmt,
                posts=len(rates),
                median_engagement_rate=round(median(known), 4) if known else None,
                average_engagement_rate=round(mean(known), 4) if known else None,
            )
        )
    return Formats(rows=sorted(result, key=lambda r: (r.platform, -r.posts)))


@router.get("/posting-consistency", response_model=PostingConsistency)
def posting_consistency(
    wh: Warehouse,
    today: Today,
    now: Now,
    weeks: Annotated[int, Query(ge=1, le=104)] = 12,
):
    start = period_start(today - timedelta(weeks=weeks - 1), "week")
    per_week = wh.fetch(
        "fct_social_posts",
        [Bucket("posted_at", "week", "period"), "platform", Agg("count", "*", "posts")],
        filters=[Filter("posted_at", ">=", start_of_day(start))],
    )
    last = wh.fetch("fct_social_posts", ["platform", Agg("max", "posted_at", "last")])
    platforms = sorted({row["platform"] for row in last})
    counts = {(row["period"], row["platform"]): int(row["posts"]) for row in per_week}
    return PostingConsistency(
        posts_per_week=TimeSeriesResponse(
            interval="week",
            start=start,
            end=today,
            unit="posts",
            series=[SeriesInfo(key=n, label=LABELS.get(n, n)) for n in platforms],
            data=[
                {"period": p, **{n: float(counts.get((p, n), 0)) for n in platforms}}
                for p in periods(start, today, "week")
            ],
        ),
        last_posts=[
            LastPost(
                platform=row["platform"],
                last_posted_at=row["last"],
                days_since=(now - row["last"]).days,
            )
            for row in sorted(last, key=lambda r: r["platform"])
        ],
    )


@router.get("/best-time", response_model=Heatmap)
def best_time(wh: Warehouse, now: Now, platform: Platform | None = None):
    """Average engagement rate by day of week and hour posted, in UK time."""
    zone = ZoneInfo(TIMEZONE)
    cells: dict = defaultdict(list)
    for post in _all_posts(wh, platform, now):
        local = post.posted_at.astimezone(zone)
        cells[(local.isoweekday(), local.hour)].append(post.engagement_rate)
    return Heatmap(
        timezone=TIMEZONE,
        metric="average_engagement_rate",
        cells=[
            HeatmapCell(
                day_of_week=day,
                hour=hour,
                count=len(cells.get((day, hour), [])),
                value=(
                    round(mean(known), 4)
                    if (
                        known := [
                            r for r in cells.get((day, hour), []) if r is not None
                        ]
                    )
                    else None
                ),
            )
            for day in range(1, 8)
            for hour in range(24)
        ],
    )


ACCOUNT_DAILY_SERIES = {
    "reach": "Reach",
    "views": "Views",
    "accounts_engaged": "Accounts engaged",
    "interactions": "Interactions",
    "link_taps": "Profile link taps",
}


@router.get("/account-daily", response_model=TimeSeriesResponse)
def account_daily(
    wh: Warehouse,
    today: Today,
    interval: Interval = "day",
    start: date | None = None,
    end: date | None = None,
):
    """Instagram account-level activity over time (TikTok's access doesn't give this)."""
    end = end or today
    start = start or end - timedelta(days=89)
    check_range(start, end, interval)
    rows = wh.fetch(
        "fct_social_account_daily",
        [
            Bucket("insight_date", interval, "period"),
            Agg("sum", "reach", "reach"),
            Agg("sum", "view_count", "views"),
            Agg("sum", "accounts_engaged", "accounts_engaged"),
            Agg("sum", "total_interactions", "interactions"),
            Agg("sum", "profile_links_taps", "link_taps"),
        ],
        filters=[
            Filter("insight_date", ">=", start),
            Filter("insight_date", "<=", end),
        ],
    )
    by_period = {row["period"]: row for row in rows}
    return TimeSeriesResponse(
        interval=interval,
        start=start,
        end=end,
        unit="count",
        series=[SeriesInfo(key=k, label=v) for k, v in ACCOUNT_DAILY_SERIES.items()],
        data=[
            {
                "period": p,
                **{
                    k: (
                        float(by_period[p][k])
                        if p in by_period and by_period[p][k] is not None
                        else None
                    )
                    for k in ACCOUNT_DAILY_SERIES
                },
            }
            for p in periods(start, end, interval)
        ],
    )


@router.get("/demographics", response_model=Demographics)
def demographics(wh: Warehouse, platform: Literal["instagram"] = "instagram"):
    """Latest follower demographics. Shares are of the followers the platform
    could classify, which can be well under the total follower count."""
    latest = wh.fetch(
        "fct_social_follower_demographics",
        [Agg("max", "ingested_at", "as_of")],
        filters=[Filter("platform", "=", platform)],
    )
    as_of = latest[0]["as_of"] if latest else None
    if as_of is None:
        return Demographics(platform=platform, as_of=None, breakdowns={})
    rows = wh.fetch(
        "fct_social_follower_demographics",
        ["breakdown_type", "breakdown_value", "follower_count"],
        filters=[Filter("platform", "=", platform), Filter("ingested_at", "=", as_of)],
        order_by=[("follower_count", "desc")],
    )
    grouped: dict = defaultdict(list)
    for row in rows:
        grouped[row["breakdown_type"]].append(row)
    breakdowns = {}
    for kind, items in grouped.items():
        total = sum(int(i["follower_count"]) for i in items)
        breakdowns[kind] = [
            DemographicBucket(
                value=i["breakdown_value"],
                followers=int(i["follower_count"]),
                share_pct=round(int(i["follower_count"]) / total * 100, 1)
                if total
                else 0.0,
            )
            for i in items
        ]
    return Demographics(platform=platform, as_of=as_of, breakdowns=breakdowns)
