"""Response models; every endpoint declares one as its `response_model`."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class MeResponse(BaseModel):
    user_id: str
    org_id: str
    role: str


class SeriesInfo(BaseModel):
    key: str
    label: str


class TimeSeriesResponse(BaseModel):
    """`data` is one flat object per period, as Recharts expects:
    {"period": "2026-10-01", "justgiving": 210.0, "launchgood": 40.0}."""

    interval: Literal["day", "week", "month"]
    start: date
    end: date
    unit: str
    series: list[SeriesInfo]
    data: list[dict[str, date | float | None]]


class MonthTotals(BaseModel):
    month_start: date
    raised: float
    donations: int
    average_gift: float | None


class FundraisingSummary(BaseModel):
    currency: Literal["GBP"]
    this_month: MonthTotals
    last_month: MonthTotals
    raised_change_pct: float | None
    excluded_non_gbp_donations: int


class FundraiserRow(BaseModel):
    project_name: str | None
    fundraiser_name: str
    source: str
    raised: float
    donations: int
    average_gift: float
    last_donation_at: datetime


class FundraiserLeaderboard(BaseModel):
    currency: Literal["GBP"]
    rows: list[FundraiserRow]


class CampaignRow(BaseModel):
    campaign_id: str
    campaign_title: str
    subject_line: str | None
    send_time: datetime | None
    emails_sent: int
    unique_opens: int | None
    open_rate: float | None
    unique_clicks: int | None
    click_rate: float | None
    click_to_open_rate: float | None
    unsubscribes: int | None
    bounces: int | None


class CampaignScorecard(BaseModel):
    rows: list[CampaignRow]
