"""Fundraising endpoints (fct_donations)."""

from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from api.data import Today, Warehouse
from api.periods import months_back, next_period, period_start, periods, start_of_day
from api.routes.common import LABELS, check_range, iso_weekday, money, optional_range
from api.schemas import (
    FundraiserLeaderboard,
    FundraiserRow,
    FundraisingSummary,
    GiftAid,
    GiftSizeBand,
    GiftSizes,
    Heatmap,
    HeatmapCell,
    MonthTotals,
    ProjectList,
    ProjectRow,
    SeriesInfo,
    TargetRow,
    Targets,
    TimeSeriesResponse,
    TrafficSourceRow,
    TrafficSources,
    Zakat,
    ZakatProjectRow,
)
from api.warehouse import TIMEZONE, Agg, Bucket, Filter, Part, RangeBucket

router = APIRouter(prefix="/fundraising", tags=["fundraising"])

# Amounts aren't converted between currencies yet; non-GBP donations are
# counted separately instead of being summed in.
GBP = Filter("currency_code", "=", "GBP")


@router.get("/summary", response_model=FundraisingSummary)
def summary(wh: Warehouse, today: Today):
    this_month = period_start(today, "month")
    last_month = months_back(today, 1)
    rows = wh.fetch(
        "fct_donations",
        [
            Bucket("donation_date", "month", "period"),
            Agg("sum", "amount", "raised"),
            Agg("count", "*", "donations"),
        ],
        filters=[
            GBP,
            Filter("donation_date", ">=", start_of_day(last_month)),
            Filter(
                "donation_date", "<", start_of_day(next_period(this_month, "month"))
            ),
        ],
    )
    by_month = {row["period"]: row for row in rows}
    last_month_end = this_month - timedelta(days=1)
    same_day = last_month.replace(day=min(today.day, last_month_end.day))
    to_date = wh.fetch(
        "fct_donations",
        [Agg("sum", "amount", "raised"), Agg("count", "*", "donations")],
        filters=[GBP, *_date_range(last_month, same_day)],
    )

    def totals(month: date, through: date, row: dict) -> MonthTotals:
        raised = money(row.get("raised"))
        donations = int(row.get("donations") or 0)
        return MonthTotals(
            month_start=month,
            through=through,
            raised=raised,
            donations=donations,
            average_gift=round(raised / donations, 2) if donations else None,
        )

    current = totals(this_month, today, by_month.get(this_month, {}))
    previous = totals(last_month, last_month_end, by_month.get(last_month, {}))
    comparable = totals(last_month, same_day, to_date[0] if to_date else {})
    excluded = wh.fetch(
        "fct_donations",
        [Agg("count", "*", "donations")],
        filters=[Filter("currency_code", "!=", "GBP")],
    )
    return FundraisingSummary(
        currency="GBP",
        this_month=current,
        last_month=previous,
        last_month_to_date=comparable,
        raised_change_pct=(
            round((current.raised - comparable.raised) / comparable.raised * 100, 1)
            if comparable.raised
            else None
        ),
        excluded_non_gbp_donations=int(excluded[0]["donations"]) if excluded else 0,
    )


@router.get("/income-over-time", response_model=TimeSeriesResponse)
def income_over_time(
    wh: Warehouse,
    today: Today,
    interval: Literal["day", "week", "month"] = "month",
    start: date | None = None,
    end: date | None = None,
):
    end = end or today
    start = start or months_back(end, 11)
    check_range(start, end, interval)

    rows = wh.fetch(
        "fct_donations",
        [
            Bucket("donation_date", interval, "period"),
            "source",
            Agg("sum", "amount", "raised"),
        ],
        filters=[
            GBP,
            Filter("donation_date", ">=", start_of_day(start)),
            Filter("donation_date", "<", start_of_day(end + timedelta(days=1))),
        ],
    )
    sources = sorted({row["source"] for row in rows})
    raised = {(row["period"], row["source"]): money(row["raised"]) for row in rows}
    data = [
        {"period": p, **{s: raised.get((p, s), 0.0) for s in sources}}
        for p in periods(start, end, interval)
    ]
    return TimeSeriesResponse(
        interval=interval,
        start=start,
        end=end,
        unit="GBP",
        series=[SeriesInfo(key=s, label=LABELS.get(s, s)) for s in sources],
        data=data,
    )


@router.get("/fundraisers", response_model=FundraiserLeaderboard)
def fundraisers(
    wh: Warehouse,
    project: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    start: date | None = None,
    end: date | None = None,
):
    """All time unless a range is given."""
    filters = [GBP, *optional_range("donation_date", start, end)]
    if project:
        filters.append(Filter("project_name", "=", project))
    rows = wh.fetch(
        "fct_donations",
        [
            "project_name",
            "fundraiser_name",
            "source",
            Agg("sum", "amount", "raised"),
            Agg("count", "*", "donations"),
            Agg("avg", "amount", "average_gift"),
            Agg("max", "donation_date", "last_donation_at"),
        ],
        filters=filters,
        order_by=[("raised", "desc")],
        limit=limit,
    )
    return FundraiserLeaderboard(
        currency="GBP",
        rows=[
            FundraiserRow(
                project_name=row["project_name"],
                fundraiser_name=row["fundraiser_name"],
                source=row["source"],
                raised=money(row["raised"]),
                donations=int(row["donations"]),
                average_gift=money(row["average_gift"]),
                last_donation_at=row["last_donation_at"],
            )
            for row in rows
        ],
    )


GIFT_SIZE_EDGES = (10, 25, 50, 100, 250)
GIFT_AID_RATE = 0.25


def _date_range(start: date, end: date) -> list[Filter]:
    return [
        Filter("donation_date", ">=", start_of_day(start)),
        Filter("donation_date", "<", start_of_day(end + timedelta(days=1))),
    ]


def _default_year(
    today: date, start: date | None, end: date | None
) -> tuple[date, date]:
    end = end or today
    return start or months_back(end, 11), end


@router.get("/projects", response_model=ProjectList)
def projects(wh: Warehouse, start: date | None = None, end: date | None = None):
    """All time unless a range is given."""
    rows = wh.fetch(
        "fct_donations",
        [
            "project_name",
            "source",
            Agg("sum", "amount", "raised"),
            Agg("count", "*", "donations"),
            Agg("count_distinct", "fundraiser_name", "fundraisers"),
            Agg("max", "donation_date", "last_donation_at"),
        ],
        filters=[GBP, *optional_range("donation_date", start, end)],
    )
    combined: dict = {}
    for row in rows:
        project = combined.setdefault(
            row["project_name"],
            {
                "raised": 0.0,
                "donations": 0,
                "fundraisers": 0,
                "sources": set(),
                "last": None,
            },
        )
        project["raised"] += float(row["raised"])
        project["donations"] += int(row["donations"])
        project["fundraisers"] += int(row["fundraisers"])
        project["sources"].add(row["source"])
        if project["last"] is None or row["last_donation_at"] > project["last"]:
            project["last"] = row["last_donation_at"]
    result = [
        ProjectRow(
            project_name=name,
            raised=money(p["raised"]),
            donations=p["donations"],
            fundraisers=p["fundraisers"],
            sources=sorted(p["sources"]),
            last_donation_at=p["last"],
        )
        for name, p in combined.items()
    ]
    return ProjectList(currency="GBP", rows=sorted(result, key=lambda r: -r.raised))


@router.get("/gift-sizes", response_model=GiftSizes)
def gift_sizes(
    wh: Warehouse, today: Today, start: date | None = None, end: date | None = None
):
    start, end = _default_year(today, start, end)
    check_range(start, end, "month")  # totals, not a daily series
    rows = wh.fetch(
        "fct_donations",
        [
            RangeBucket("amount", GIFT_SIZE_EDGES, "band"),
            Agg("count", "*", "donations"),
            Agg("sum", "amount", "raised"),
        ],
        filters=[GBP, *_date_range(start, end)],
    )
    by_band = {int(row["band"]): row for row in rows}
    lows = (0, *GIFT_SIZE_EDGES)
    highs = (*GIFT_SIZE_EDGES, None)
    bands = []
    for index, (low, high) in enumerate(zip(lows, highs, strict=True)):
        row = by_band.get(index, {})
        bands.append(
            GiftSizeBand(
                band=f"£{low}–{high}" if high else f"£{low}+",
                min_amount=low,
                max_amount=high,
                donations=int(row.get("donations") or 0),
                raised=money(row.get("raised")),
            )
        )
    return GiftSizes(currency="GBP", bands=bands)


@router.get("/gift-aid", response_model=GiftAid)
def gift_aid(
    wh: Warehouse, today: Today, start: date | None = None, end: date | None = None
):
    """LaunchGood records the Gift Aid flag per donation; JustGiving only gives
    its own page-level estimate, reported separately."""
    start, end = _default_year(today, start, end)
    check_range(start, end, "month")
    launchgood = [Filter("source", "=", "launchgood"), GBP, *_date_range(start, end)]
    month_totals = [
        Bucket("donation_date", "month", "period"),
        Agg("sum", "amount", "raised"),
        Agg("count", "*", "donations"),
    ]
    everything = wh.fetch("fct_donations", month_totals, filters=launchgood)
    eligible = wh.fetch(
        "fct_donations",
        month_totals,
        filters=[*launchgood, Filter("is_gift_aid", "=", True)],
    )
    estimate = wh.fetch(
        "dim_fundraising_pages",
        [Agg("sum", "total_estimated_gift_aid", "estimate")],
        filters=[Filter("currency_code", "=", "GBP")],
    )

    eligible_by_month = {row["period"]: money(row["raised"]) for row in eligible}
    eligible_amount = sum(eligible_by_month.values())
    with_gift_aid = sum(int(row["donations"]) for row in eligible)
    donations = sum(int(row["donations"]) for row in everything)
    return GiftAid(
        currency="GBP",
        start=start,
        end=end,
        eligible_amount=money(eligible_amount),
        claim_value=money(eligible_amount * GIFT_AID_RATE),
        donations_with_gift_aid=with_gift_aid,
        donations=donations,
        gift_aid_share_pct=round(with_gift_aid / donations * 100, 1)
        if donations
        else None,
        justgiving_estimated_gift_aid=money(estimate[0]["estimate"] if estimate else 0),
        data=[
            {
                "period": p,
                "eligible_amount": eligible_by_month.get(p, 0.0),
                "claim_value": money(eligible_by_month.get(p, 0.0) * GIFT_AID_RATE),
            }
            for p in periods(start, end, "month")
        ],
    )


@router.get("/zakat", response_model=Zakat)
def zakat(
    wh: Warehouse, today: Today, start: date | None = None, end: date | None = None
):
    start, end = _default_year(today, start, end)
    check_range(start, end, "month")  # totals, not a daily series
    rows = wh.fetch(
        "fct_donations",
        [
            "project_name",
            Agg("sum", "zakat_amount", "zakat"),
            Agg("count", "*", "donations"),
        ],
        filters=[GBP, Filter("is_zakat", "=", True), *_date_range(start, end)],
        order_by=[("zakat", "desc")],
    )
    by_project = [
        ZakatProjectRow(
            project_name=row["project_name"],
            zakat=money(row["zakat"]),
            donations=int(row["donations"]),
        )
        for row in rows
    ]
    return Zakat(
        currency="GBP",
        total_zakat=money(sum(r.zakat for r in by_project)),
        donations=sum(r.donations for r in by_project),
        by_project=by_project,
    )


@router.get("/fees", response_model=TimeSeriesResponse)
def fees(
    wh: Warehouse, today: Today, start: date | None = None, end: date | None = None
):
    """Gross vs net per month. LaunchGood only: JustGiving doesn't report fees."""
    start, end = _default_year(today, start, end)
    check_range(start, end, "month")
    rows = wh.fetch(
        "fct_donations",
        [
            Bucket("donation_date", "month", "period"),
            Agg("sum", "amount", "gross"),
            Agg("sum", "net_amount", "net"),
            Agg("sum", "processing_fees", "fees"),
        ],
        filters=[
            Filter("source", "=", "launchgood"),
            GBP,
            Filter("settlement_currency", "=", "GBP"),
            *_date_range(start, end),
        ],
    )
    by_month = {row["period"]: row for row in rows}
    keys = ("gross", "net", "fees")
    return TimeSeriesResponse(
        interval="month",
        start=start,
        end=end,
        unit="GBP",
        series=[SeriesInfo(key=k, label=k.capitalize()) for k in keys],
        data=[
            {"period": p, **{k: money(by_month.get(p, {}).get(k)) for k in keys}}
            for p in periods(start, end, "month")
        ],
    )


@router.get("/traffic-sources", response_model=TrafficSources)
def traffic_sources(
    wh: Warehouse, today: Today, start: date | None = None, end: date | None = None
):
    start, end = _default_year(today, start, end)
    check_range(start, end, "month")  # totals, not a daily series
    rows = wh.fetch(
        "fct_donations",
        [
            "source",
            "traffic_source",
            Agg("sum", "amount", "raised"),
            Agg("count", "*", "donations"),
        ],
        filters=[GBP, *_date_range(start, end)],
        order_by=[("raised", "desc")],
    )
    return TrafficSources(
        currency="GBP",
        rows=[
            TrafficSourceRow(
                source=row["source"],
                traffic_source=row["traffic_source"],
                raised=money(row["raised"]),
                donations=int(row["donations"]),
            )
            for row in rows
        ],
    )


@router.get("/targets", response_model=Targets)
def targets(wh: Warehouse):
    """JustGiving pages that have a target. LaunchGood exports don't include one."""
    rows = wh.fetch(
        "dim_fundraising_pages",
        [
            "fundraiser_name",
            "project_name",
            "page_status",
            "fundraising_target",
            "total_raised",
        ],
        filters=[
            Filter("currency_code", "=", "GBP"),
            Filter("fundraising_target", ">", 0.0),
        ],
    )
    result = [
        TargetRow(
            fundraiser_name=row["fundraiser_name"],
            project_name=row["project_name"],
            page_status=row["page_status"],
            target=money(row["fundraising_target"]),
            raised=money(row["total_raised"]),
            progress_pct=round(
                float(row["total_raised"] or 0)
                / float(row["fundraising_target"])
                * 100,
                1,
            ),
        )
        for row in rows
    ]
    return Targets(currency="GBP", rows=sorted(result, key=lambda r: -r.progress_pct))


@router.get("/timing", response_model=Heatmap)
def timing(
    wh: Warehouse, today: Today, start: date | None = None, end: date | None = None
):
    """Donations by day of week and hour, in UK time."""
    start, end = _default_year(today, start, end)
    check_range(start, end, "month")  # totals, not a daily series
    rows = wh.fetch(
        "fct_donations",
        [
            Part("donation_date", "dayofweek", "dow"),
            Part("donation_date", "hour", "hour"),
            Agg("count", "*", "donations"),
            Agg("sum", "amount", "raised"),
        ],
        filters=[GBP, *_date_range(start, end)],
    )
    by_cell = {(iso_weekday(int(r["dow"])), int(r["hour"])): r for r in rows}
    return Heatmap(
        timezone=TIMEZONE,
        metric="raised",
        cells=[
            HeatmapCell(
                day_of_week=day,
                hour=hour,
                count=int(by_cell.get((day, hour), {}).get("donations") or 0),
                value=money(by_cell.get((day, hour), {}).get("raised")),
            )
            for day in range(1, 8)
            for hour in range(24)
        ],
    )
