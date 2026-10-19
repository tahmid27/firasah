"""Email endpoints (fct_mailchimp_*)."""

from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query, status

from api.data import Today, Warehouse
from api.periods import months_back, periods, start_of_day
from api.routes.common import check_range, money, optional_range
from api.schemas import (
    CampaignLinks,
    CampaignRow,
    CampaignScorecard,
    HourRow,
    LinkRow,
    SendTimes,
    SeriesInfo,
    TimeSeriesResponse,
)
from api.warehouse import TIMEZONE, Agg, Bucket, Filter, Part

router = APIRouter(prefix="/email", tags=["email"])


@router.get("/campaigns", response_model=CampaignScorecard)
def campaigns(
    wh: Warehouse,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    start: date | None = None,
    end: date | None = None,
):
    """Newest first; sent in the range when one is given."""
    rows = wh.fetch(
        "fct_mailchimp_campaigns",
        [
            "campaign_id",
            "campaign_title",
            "subject_line",
            "send_time",
            "emails_sent",
            "unique_opens",
            "open_rate",
            "unique_clicks",
            "click_rate",
            "unsubscribe_count",
            "hard_bounces",
            "soft_bounces",
        ],
        filters=optional_range("send_time", start, end),
        order_by=[("send_time", "desc")],
        limit=limit,
    )
    return CampaignScorecard(
        rows=[
            CampaignRow(
                campaign_id=row["campaign_id"],
                campaign_title=row["campaign_title"],
                subject_line=row["subject_line"],
                send_time=row["send_time"],
                emails_sent=row["emails_sent"],
                unique_opens=row["unique_opens"],
                open_rate=row["open_rate"],
                unique_clicks=row["unique_clicks"],
                click_rate=row["click_rate"],
                click_to_open_rate=(
                    round(row["unique_clicks"] / row["unique_opens"], 4)
                    if row["unique_opens"]
                    else None
                ),
                unsubscribes=row["unsubscribe_count"],
                bounces=(row["hard_bounces"] or 0) + (row["soft_bounces"] or 0),
            )
            for row in rows
        ]
    )


@router.get("/audience-growth", response_model=TimeSeriesResponse)
def audience_growth(
    wh: Warehouse,
    today: Today,
    interval: Literal["day", "week", "month"] = "week",
    start: date | None = None,
    end: date | None = None,
):
    """Subscribes and unsubscribes per period. Mailchimp's daily figures count
    form sign-ups only: contacts added by hand or imported don't appear."""
    end = end or today
    start = start or end - timedelta(days=89)
    check_range(start, end, interval)
    rows = wh.fetch(
        "fct_mailchimp_audience_daily",
        [
            Bucket("activity_date", interval, "period"),
            Agg("sum", "new_subscribers", "new_subscribers"),
            Agg("sum", "unsubscribes", "unsubscribes"),
            Agg("sum", "net_subscribers", "net"),
        ],
        filters=[
            Filter("activity_date", ">=", start),
            Filter("activity_date", "<=", end),
        ],
    )
    keys = {
        "new_subscribers": "New subscribers",
        "unsubscribes": "Unsubscribes",
        "net": "Net change",
    }
    by_period = {row["period"]: row for row in rows}
    return TimeSeriesResponse(
        interval=interval,
        start=start,
        end=end,
        unit="subscribers",
        series=[SeriesInfo(key=k, label=v) for k, v in keys.items()],
        data=[
            {
                "period": p,
                # No row means Mailchimp sent nothing for that period: unknown, not 0
                **{k: float(by_period[p][k]) if p in by_period else None for k in keys},
            }
            for p in periods(start, end, interval)
        ],
    )


@router.get("/campaigns/{campaign_id}/links", response_model=CampaignLinks)
def campaign_links(
    wh: Warehouse,
    campaign_id: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")],
):
    campaign = wh.fetch(
        "fct_mailchimp_campaigns",
        ["campaign_id", "campaign_title"],
        filters=[Filter("campaign_id", "=", campaign_id)],
        limit=1,
    )
    if not campaign:
        # 404 whether it doesn't exist or belongs to another charity, so the
        # answer never reveals another charity's campaign exists
        raise HTTPException(status.HTTP_404_NOT_FOUND, "campaign not found")
    rows = wh.fetch(
        "fct_mailchimp_link_clicks",
        ["url", "total_clicks", "unique_clicks"],
        filters=[Filter("campaign_id", "=", campaign_id)],
        order_by=[("total_clicks", "desc")],
    )
    total = sum(int(r["total_clicks"]) for r in rows)
    return CampaignLinks(
        campaign_id=campaign[0]["campaign_id"],
        campaign_title=campaign[0]["campaign_title"],
        rows=[
            LinkRow(
                url=r["url"],
                total_clicks=int(r["total_clicks"]),
                unique_clicks=int(r["unique_clicks"]),
                share_of_clicks_pct=round(int(r["total_clicks"]) / total * 100, 1)
                if total
                else None,
            )
            for r in rows
        ],
    )


@router.get("/list-health", response_model=TimeSeriesResponse)
def list_health(
    wh: Warehouse, today: Today, months: Annotated[int, Query(ge=1, le=36)] = 12
):
    """Monthly subscribed, unsubscribed, cleaned (dead) addresses, and bounces."""
    start, end = months_back(today, months - 1), today
    growth = wh.fetch(
        "fct_mailchimp_audience_monthly",
        [
            "month_start",
            Agg("sum", "subscribed", "subscribed"),
            Agg("sum", "unsubscribed", "unsubscribed"),
            Agg("sum", "cleaned", "cleaned"),
        ],
        filters=[Filter("month_start", ">=", start)],
    )
    bounces = wh.fetch(
        "fct_mailchimp_campaigns",
        [
            Bucket("send_time", "month", "period"),
            Agg("sum", "hard_bounces", "hard"),
            Agg("sum", "soft_bounces", "soft"),
        ],
        filters=[Filter("send_time", ">=", start_of_day(start))],
    )
    by_month = {row["month_start"]: row for row in growth}
    bounced = {
        row["period"]: (row["hard"] or 0) + (row["soft"] or 0) for row in bounces
    }
    keys = {
        "subscribed": "Subscribed",
        "unsubscribed": "Unsubscribed",
        "cleaned": "Cleaned",
        "bounces": "Bounces",
    }
    return TimeSeriesResponse(
        interval="month",
        start=start,
        end=end,
        unit="contacts",
        series=[SeriesInfo(key=k, label=v) for k, v in keys.items()],
        data=[
            {
                "period": p,
                **{
                    k: float(by_month[p][k]) if p in by_month else None
                    for k in ("subscribed", "unsubscribed", "cleaned")
                },
                "bounces": float(bounced.get(p, 0)),
            }
            for p in periods(start, end, "month")
        ],
    )


@router.get("/send-times", response_model=SendTimes)
def send_times(wh: Warehouse, start: date | None = None, end: date | None = None):
    """When supporters open and click: by hours after sending (averaged across
    campaigns) and by hour of day in UK time (totals). With a range: activity
    in that range."""
    in_range = optional_range("hour_start", start, end)
    after = wh.fetch(
        "fct_mailchimp_campaign_hourly",
        [
            "hours_after_send",
            Agg("avg", "unique_opens", "opens"),
            Agg("avg", "recipient_clicks", "clicks"),
            Agg("count_distinct", "campaign_id", "campaigns"),
        ],
        filters=in_range,
        order_by=[("hours_after_send", "asc")],
    )
    of_day = wh.fetch(
        "fct_mailchimp_campaign_hourly",
        [
            Part("hour_start", "hour", "hour"),
            Agg("sum", "unique_opens", "opens"),
            Agg("sum", "recipient_clicks", "clicks"),
        ],
        filters=in_range,
    )
    by_hour = {int(r["hour"]): r for r in of_day}
    return SendTimes(
        campaigns=max((int(r["campaigns"]) for r in after), default=0),
        by_hours_after_send=[
            HourRow(
                hour=int(r["hours_after_send"]),
                opens=money(r["opens"]),
                clicks=money(r["clicks"]),
            )
            for r in after
        ],
        by_hour_of_day=[
            HourRow(
                hour=h,
                opens=float(by_hour.get(h, {}).get("opens") or 0),
                clicks=float(by_hour.get(h, {}).get("clicks") or 0),
            )
            for h in range(24)
        ],
        timezone=TIMEZONE,
    )
