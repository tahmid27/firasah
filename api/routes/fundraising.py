"""Fundraising endpoints (fct_donations)."""

from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from api.data import Today, Warehouse
from api.periods import months_back, next_period, period_start, periods, start_of_day
from api.routes.common import LABELS, check_range, money
from api.schemas import (
    FundraiserLeaderboard,
    FundraiserRow,
    FundraisingSummary,
    MonthTotals,
    SeriesInfo,
    TimeSeriesResponse,
)
from api.warehouse import Agg, Bucket, Filter

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

    def totals(month: date) -> MonthTotals:
        row = by_month.get(month, {})
        raised = money(row.get("raised"))
        donations = int(row.get("donations") or 0)
        return MonthTotals(
            month_start=month,
            raised=raised,
            donations=donations,
            average_gift=round(raised / donations, 2) if donations else None,
        )

    current, previous = totals(this_month), totals(last_month)
    excluded = wh.fetch(
        "fct_donations",
        [Agg("count", "*", "donations")],
        filters=[Filter("currency_code", "!=", "GBP")],
    )
    return FundraisingSummary(
        currency="GBP",
        this_month=current,
        last_month=previous,
        raised_change_pct=(
            round((current.raised - previous.raised) / previous.raised * 100, 1)
            if previous.raised
            else None
        ),
        excluded_non_gbp_donations=int(excluded[0]["donations"]) if excluded else 0,
    )


@router.get("/income-over-time", response_model=TimeSeriesResponse)
def income_over_time(
    wh: Warehouse,
    today: Today,
    interval: Literal["week", "month"] = "month",
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
):
    filters = [GBP]
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
