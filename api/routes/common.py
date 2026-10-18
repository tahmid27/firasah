"""Helpers shared by the data endpoints."""

from datetime import date

from fastapi import HTTPException, status

MAX_PERIODS = 400

LABELS = {
    "justgiving": "JustGiving",
    "launchgood": "LaunchGood",
    "instagram": "Instagram",
    "tiktok": "TikTok",
}


SOURCES = ("justgiving", "launchgood", "instagram", "tiktok", "mailchimp")
LABELS["mailchimp"] = "Mailchimp"


def money(value) -> float:
    return round(float(value or 0), 2)


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def iso_weekday(bigquery_dayofweek: int) -> int:
    """BigQuery's DAYOFWEEK (1 = Sunday) as ISO (1 = Monday ... 7 = Sunday)."""
    return (bigquery_dayofweek + 5) % 7 + 1


def latest_total(readings: dict[str, list[tuple]], on_or_before=None) -> float | None:
    """Sum across accounts of each account's latest (day, value) reading, optionally
    no later than a cutoff. None if any account has no reading in range."""
    total = 0.0
    for points in readings.values():
        eligible = [
            v for day, v in points if on_or_before is None or day <= on_or_before
        ]
        if not eligible:
            return None
        total += eligible[-1]
    return total if readings else None


def check_range(start: date, end: date, interval: str) -> None:
    if start > end:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "start must be on or before end"
        )
    days = (end - start).days
    count = {
        "day": days + 1,
        "week": days // 7 + 2,
        "month": (end.year - start.year) * 12 + end.month - start.month + 1,
    }[interval]
    if count > MAX_PERIODS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"range too long: {count} {interval}s (max {MAX_PERIODS})",
        )
