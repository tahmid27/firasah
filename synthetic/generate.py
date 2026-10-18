"""Generates every raw batch for one charity, in the order the pipeline would."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from ingestion.refresh import REFRESH_RUNS_SCHEMA
from synthetic import justgiving, launchgood, mailchimp, social
from synthetic.batches import Batch
from synthetic.charities import Charity
from synthetic.donations import donations_for
from synthetic.marketing import daily_lift, emails_for, posts_for
from synthetic.rand import rng

YEARS = 3


@dataclass
class Generated:
    charity: Charity
    batches: list[Batch]
    donations: int
    emails: int
    posts: int


def _refresh_runs(c: Charity, end: date, seed: int) -> Batch:
    r = rng(seed, c.org_id, "refresh-runs")
    sources = [*c.donation_platforms, *c.social, "mailchimp"]
    failures = {("instagram", 12): 400, ("instagram", 11): 400, ("tiktok", 25): 401}
    rows = []
    for days_ago in range(60, 0, -1):
        day = end - timedelta(days=days_ago - 1)
        started = datetime.combine(day, time(6, 0), tzinfo=UTC)
        for i, source in enumerate(sorted(sources)):
            at = started + timedelta(seconds=20 * i + r.randint(0, 9))
            failed = failures.get((source, days_ago))
            status = "failed" if failed else "success"
            if source == "launchgood" and days_ago not in (1, 31):
                status = "skipped"  # no new export uploaded
            rows.append(
                {
                    "source": source,
                    "status": status,
                    "started_at": at.isoformat(),
                    "finished_at": (
                        at + timedelta(seconds=r.randint(2, 15))
                    ).isoformat(),
                    "error_type": "HTTPStatusError" if failed else None,
                    "http_status": failed,
                }
            )
    return Batch(
        "raw_refresh_runs",
        rows,
        ingested_at=datetime.combine(end, time(7), tzinfo=UTC),
        schema=REFRESH_RUNS_SCHEMA,
    )


def generate(
    c: Charity, end: date, seed: int, out_dir: Path, years: int = YEARS
) -> Generated:
    start = end - timedelta(days=365 * years)
    pulled = datetime.combine(end, time(6), tzinfo=UTC)

    emails = emails_for(c, start, end, seed)
    posts = {
        platform: posts_for(c, platform, start, end, seed) for platform in c.social
    }
    lift = daily_lift(emails, [p for ps in posts.values() for p in ps])
    donations = {
        platform: donations_for(c, platform, start, end, lift, seed)
        for platform in c.donation_platforms
    }

    batches: list[Batch] = []
    batches += justgiving.batches(c, donations.get("justgiving", []), pulled, seed)
    batches += launchgood.batches(
        c, donations.get("launchgood", []), pulled, out_dir / c.org_id, seed
    )
    if "instagram" in posts:
        batches += social.instagram_batches(c, posts["instagram"], start, end, seed)
    if "tiktok" in posts:
        batches += social.tiktok_batches(c, posts["tiktok"], start, end, seed)
    batches += mailchimp.batches(c, emails, start, end, seed)
    batches.append(_refresh_runs(c, end, seed))
    return Generated(
        charity=c,
        batches=batches,
        donations=sum(len(d) for d in donations.values()),
        emails=len(emails),
        posts=sum(len(p) for p in posts.values()),
    )
