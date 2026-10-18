"""Dates that move giving: Islamic calendar (UK moon-sighting dates), December,
Giving Tuesday, paydays."""

from datetime import date, timedelta

# (first day of Ramadan, Eid al-Fitr). Eid dates from UK mosque announcements;
# Ramadan starts are the day after the preceding new-moon sighting.
RAMADAN = (
    (date(2024, 3, 11), date(2024, 4, 10)),
    (date(2025, 3, 1), date(2025, 3, 30)),
    (date(2026, 2, 19), date(2026, 3, 21)),
)
# Eid al-Adha (10 Dhul Hijjah); the first ten days of Dhul Hijjah end on it
EID_AL_ADHA = (date(2024, 6, 16), date(2025, 6, 6), date(2026, 5, 27))
GIVING_TUESDAY = (date(2023, 11, 28), date(2024, 12, 3), date(2025, 12, 2))


def ramadan_day(day: date) -> int | None:
    """1-based day of Ramadan, or None outside Ramadan."""
    for start, eid in RAMADAN:
        if start <= day < eid:
            return (day - start).days + 1
    return None


def ramadan_length(day: date) -> int | None:
    for start, eid in RAMADAN:
        if start <= day < eid:
            return (eid - start).days
    return None


def in_last_ten_nights(day: date) -> bool:
    n, length = ramadan_day(day), ramadan_length(day)
    return n is not None and n > length - 10


def is_27th_night(day: date) -> bool:
    return ramadan_day(day) == 27


def in_dhul_hijjah_ten(day: date) -> bool:
    return any(eid - timedelta(days=9) <= day <= eid for eid in EID_AL_ADHA)


def is_payday_window(day: date) -> bool:
    """The last Friday of the month and the weekend after it."""
    next_month = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_day = next_month - timedelta(days=1)
    last_friday = last_day - timedelta(days=(last_day.weekday() - 4) % 7)
    return last_friday <= day <= last_friday + timedelta(days=2)


def in_ramadan(day: date) -> bool:
    return ramadan_day(day) is not None
