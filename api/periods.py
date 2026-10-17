"""Date helpers for time-series endpoints."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta


def period_start(day: date, grain: str) -> date:
    if grain == "day":
        return day
    if grain == "week":
        return day - timedelta(days=day.weekday())
    if grain == "month":
        return day.replace(day=1)
    raise ValueError(f"unknown grain: {grain!r}")


def next_period(start: date, grain: str) -> date:
    if grain == "day":
        return start + timedelta(days=1)
    if grain == "week":
        return start + timedelta(weeks=1)
    if start.month == 12:
        return start.replace(year=start.year + 1, month=1)
    return start.replace(month=start.month + 1)


def periods(start: date, end: date, grain: str) -> Iterator[date]:
    """Every period start from the one containing `start` to the one containing `end`."""
    current = period_start(start, grain)
    while current <= end:
        yield current
        current = next_period(current, grain)


def months_back(day: date, months: int) -> date:
    """First day of the month `months` before the month containing `day`."""
    index = day.year * 12 + day.month - 1 - months
    return date(index // 12, index % 12 + 1, 1)


def start_of_day(day: date) -> datetime:
    """For filtering TIMESTAMP columns, which can't be compared with a DATE."""
    return datetime.combine(day, time.min, tzinfo=UTC)
