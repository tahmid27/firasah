"""Reproducible randomness: every generator gets its own stream derived from
one seed, so changing one source doesn't reshuffle the others."""

import hashlib
import random
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")


def rng(seed: int, *parts: object) -> random.Random:
    digest = hashlib.sha256(":".join(map(str, (seed, *parts))).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def weighted(r: random.Random, options: dict):
    return r.choices(list(options), weights=list(options.values()))[0]


def uk_time_to_utc(day: date, hour: int, minute: int, second: int = 0) -> datetime:
    local = datetime.combine(day, time(hour, minute, second), tzinfo=UK)
    return local.astimezone(UTC)


def audience_series(
    r: random.Random,
    start: date,
    end: date,
    counts: tuple[int, int],
    bumps: dict[date, float] | None = None,
    drops: dict[date, float] | None = None,
) -> dict[date, int]:
    """A follower or subscriber count that goes from counts[0] to counts[1] the
    way real audiences do: growth that speeds up and slows down over weeks,
    bumps that fade over a few days (bumps: day -> extra growth, 1.0 = a
    normal day's worth again), and one-day losses (drops: day -> share of the
    audience lost, e.g. unsubscribes after a send or a platform purge).
    Gains are scaled so the last day lands within ±0.5% of counts[1] (nudged
    off the round configured number)."""
    from datetime import timedelta

    bumps, drops = bumps or {}, drops or {}
    # Real counts don't land on round numbers; nudge the end by up to ±0.5%
    counts = (counts[0], round(counts[1] * r.uniform(0.995, 1.005)))
    days = (end - start).days or 1
    smooth = [
        counts[0] * (counts[1] / counts[0]) ** (i / days) for i in range(days + 1)
    ]
    pace, carry, gains, losses = 0.0, 0.0, [], []
    for i in range(1, days + 1):
        day = start + timedelta(days=i)
        pace = 0.93 * pace + r.gauss(0, 0.22)  # weeks-long fast and slow spells
        carry = 0.6 * carry + bumps.get(day, 0.0)  # a bump fades over days
        gains.append(
            max(0.0, (1 + carry) * pow(2.718281828, pace) * r.uniform(0.6, 1.4))
        )
        losses.append(smooth[i] * drops.get(day, 0.0))
    needed = counts[1] - counts[0] + sum(losses)
    scale = needed / sum(gains) if sum(gains) else 0.0
    series, level = {start: counts[0]}, float(counts[0])
    for i in range(1, days + 1):
        level += gains[i - 1] * scale - losses[i - 1]
        series[start + timedelta(days=i)] = max(1, round(level))
    return series
