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


def money(value) -> float:
    return round(float(value or 0), 2)


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
