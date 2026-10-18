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
