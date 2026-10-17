"""Social endpoints (fct_social_*)."""

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter

from api.data import Today, Warehouse
from api.periods import periods, start_of_day
from api.routes.common import LABELS, check_range
from api.schemas import SeriesInfo, TimeSeriesResponse
from api.warehouse import Agg, Bucket, Filter

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
