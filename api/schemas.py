"""Response models; every endpoint declares one as its `response_model`."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class MeResponse(BaseModel):
    user_id: str
    org_id: str
    org_name: str | None
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
    through: date  # last day counted (today, for the current month)
    raised: float
    donations: int
    average_gift: float | None


class FundraisingSummary(BaseModel):
    currency: Literal["GBP"]
    this_month: MonthTotals
    last_month: MonthTotals
    # The same days of last month as this month has had so far, so a part
    # month is never compared with a whole one
    last_month_to_date: MonthTotals
    raised_change_pct: float | None  # this month vs last_month_to_date
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


# --- overview ------------------------------------------------------------------


class TrendPoint(BaseModel):
    day: date
    value: float | None  # None before the first reading


class MetricChange(BaseModel):
    value: float | None
    previous: float | None
    change: float | None
    change_pct: float | None
    # Daily total for the last 90 days, each account's latest reading carried
    # forward, so a day one account wasn't read doesn't show as a dip
    trend: list[TrendPoint]


class OverviewSummary(BaseModel):
    followers: MetricChange
    email_subscribers: MetricChange
    compared_with: date


class SourceStatus(BaseModel):
    source: str
    label: str
    last_data_at: datetime | None
    last_run_at: datetime | None
    last_run_status: str | None
    last_error_type: str | None
    last_http_status: int | None
    last_success_at: datetime | None
    hours_since_data: float | None


class DataHealth(BaseModel):
    sources: list[SourceStatus]


# --- fundraising -----------------------------------------------------------------


class ProjectRow(BaseModel):
    project_name: str | None
    raised: float
    donations: int
    fundraisers: int
    sources: list[str]
    last_donation_at: datetime


class ProjectList(BaseModel):
    currency: Literal["GBP"]
    rows: list[ProjectRow]


class GiftSizeBand(BaseModel):
    band: str
    min_amount: float
    max_amount: float | None
    donations: int
    raised: float


class GiftSizes(BaseModel):
    currency: Literal["GBP"]
    bands: list[GiftSizeBand]


class GiftAid(BaseModel):
    currency: Literal["GBP"]
    start: date
    end: date
    eligible_amount: float
    claim_value: float
    donations_with_gift_aid: int
    donations: int
    gift_aid_share_pct: float | None
    justgiving_estimated_gift_aid: float
    data: list[dict[str, date | float | None]]


class ZakatProjectRow(BaseModel):
    project_name: str | None
    zakat: float
    donations: int


class Zakat(BaseModel):
    currency: Literal["GBP"]
    total_zakat: float
    donations: int
    by_project: list[ZakatProjectRow]


class TrafficSourceRow(BaseModel):
    source: str
    traffic_source: str | None
    raised: float
    donations: int


class TrafficSources(BaseModel):
    currency: Literal["GBP"]
    rows: list[TrafficSourceRow]


class TargetRow(BaseModel):
    fundraiser_name: str
    project_name: str | None
    page_status: str | None
    target: float
    raised: float
    progress_pct: float


class Targets(BaseModel):
    currency: Literal["GBP"]
    rows: list[TargetRow]


class HeatmapCell(BaseModel):
    day_of_week: int  # 1 = Monday ... 7 = Sunday
    hour: int
    count: int
    value: float | None


class Heatmap(BaseModel):
    timezone: str
    metric: str
    cells: list[HeatmapCell]


# --- social ----------------------------------------------------------------------


class PostRow(BaseModel):
    post_id: str
    platform: str
    posted_at: datetime
    format: str
    caption: str | None
    permalink: str | None
    views: int | None
    reach: int | None
    likes: int | None
    comments: int | None
    shares: int | None
    saves: int | None
    engagement_rate: float | None
    view_to_like_rate: float | None


class Posts(BaseModel):
    engagement_basis: str
    rows: list[PostRow]


class FormatRow(BaseModel):
    platform: str
    format: str
    posts: int
    median_engagement_rate: float | None
    average_engagement_rate: float | None


class Formats(BaseModel):
    rows: list[FormatRow]


class LastPost(BaseModel):
    platform: str
    last_posted_at: datetime
    days_since: int


class PostingConsistency(BaseModel):
    posts_per_week: TimeSeriesResponse
    last_posts: list[LastPost]


class DemographicBucket(BaseModel):
    value: str
    followers: int
    share_pct: float


class Demographics(BaseModel):
    platform: str
    as_of: datetime | None
    breakdowns: dict[str, list[DemographicBucket]]


# --- email -----------------------------------------------------------------------


class LinkRow(BaseModel):
    url: str
    total_clicks: int
    unique_clicks: int
    share_of_clicks_pct: float | None


class CampaignLinks(BaseModel):
    campaign_id: str
    campaign_title: str
    rows: list[LinkRow]


class HourRow(BaseModel):
    hour: int
    opens: float
    clicks: float


class SendTimes(BaseModel):
    campaigns: int
    by_hours_after_send: list[HourRow]
    by_hour_of_day: list[HourRow]
    timezone: str


# --- appeals ---------------------------------------------------------------------


class TimelineEvent(BaseModel):
    at: datetime
    kind: Literal["post", "email"]
    platform: str
    title: str | None
    link: str | None


class AppealTimeline(BaseModel):
    donations: TimeSeriesResponse
    events: list[TimelineEvent]


class WindowStats(BaseModel):
    start: date
    end: date
    raised: float
    donations: int
    posts: int
    emails: int
    follower_change: float | None


class WindowReport(BaseModel):
    currency: Literal["GBP"]
    current: WindowStats
    previous: WindowStats
    raised_change_pct: float | None


class EmailLiftRow(BaseModel):
    campaign_id: str
    campaign_title: str
    send_time: datetime
    raised_2_days: float  # the day of sending and the day after
    donations_2_days: int
    typical_2_days: float | None
    lift_pct: float | None


class EmailLift(BaseModel):
    currency: Literal["GBP"]
    baseline_days: int
    rows: list[EmailLiftRow]
