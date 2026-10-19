"""The synthetic generator: raw shapes match the real APIs, and the promised
patterns are there."""

import json
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from synthetic import calendar
from synthetic.charities import CHARITIES
from synthetic.generate import generate

REFERENCE = json.loads(Path("synthetic/reference_shapes.json").read_text())
END = date(2026, 10, 17)

# Columns the connectors add when loading, not part of the API record
LOAD_TAGS = {"_page_short_name", "_ig_user_id", "_source_file"}
# Fields real responses omit sometimes (e.g. Instagram drops `caption` when empty)
SOMETIMES_ABSENT = {"instagram_media": {"caption"}}
# Fields we can't pull yet, included on purpose (see the capability reference)
NOT_YET_PULLED = {
    "tiktok_videos": {"embed_link", "embed_html", "height", "width", "is_aigc"},
    "tiktok_user_info": {
        "union_id",
        "avatar_url",
        "avatar_url_100",
        "avatar_large_url",
        "username",
        "bio_description",
        "profile_deep_link",
        "is_verified",
    },
}
# Whole tables for data we can't pull yet: no real sample to compare against
RAW_ONLY = {
    "raw_instagram_stories",
    "raw_tiktok_video_insights",
    "raw_tiktok_account_insights_daily",
}
FIRASAH_OWN = {"raw_refresh_runs"}


def key_paths(record: dict, prefix: str = "") -> set[str]:
    paths = set()
    for key, value in record.items():
        paths.add(prefix + key)
        if isinstance(value, dict):
            paths |= key_paths(value, prefix + key + ".")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for item in value:
                paths |= key_paths(item, prefix + key + "[].")
    return paths


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("synthetic")
    return {c.org_id: generate(c, END, seed=7, out_dir=out, years=1) for c in CHARITIES}


def all_batches(generated):
    return [(org, b) for org, g in generated.items() for b in g.batches]


def test_every_table_is_accounted_for(generated):
    tables = {b.table for _, b in all_batches(generated)}
    known = {
        f"raw_{name}" for name in REFERENCE if name != "launchgood_export_csv_header"
    }
    assert tables - known - RAW_ONLY - FIRASAH_OWN == set()
    # every real source table is produced by at least one charity
    assert known <= tables


def test_records_have_exactly_the_real_apis_field_names(generated):
    problems = []
    for org, batch in all_batches(generated):
        name = batch.table.removeprefix("raw_")
        if batch.table in RAW_ONLY | FIRASAH_OWN:
            continue
        shape = REFERENCE[name]
        required = set(shape["required"]) - SOMETIMES_ABSENT.get(name, set())
        allowed = (
            set(shape["required"])
            | set(shape["optional"])
            | NOT_YET_PULLED.get(name, set())
        )
        for record in batch.rows[:200]:
            paths = key_paths({k: v for k, v in record.items() if k not in LOAD_TAGS})
            missing, extra = required - paths, paths - allowed
            if missing or extra:
                problems.append(
                    f"{org} {name}: missing {sorted(missing)[:5]} extra {sorted(extra)[:5]}"
                )
                break
    assert problems == []


def test_launchgood_export_has_the_real_header(generated):
    for org in ("demo_small", "demo_large"):
        files = [
            b for b in generated[org].batches if b.table == "raw_launchgood_donations"
        ]
        assert len(files) == 2  # an older export and an overlapping newer one
        assert set(files[1].rows[0]) == set(
            REFERENCE["launchgood_donations"]["required"]
        )


def test_generation_is_reproducible(tmp_path):
    c = CHARITIES[0]
    a = generate(c, END, seed=3, out_dir=tmp_path / "a", years=1)
    b = generate(c, END, seed=3, out_dir=tmp_path / "b", years=1)
    assert [(x.table, len(x.rows)) for x in a.batches] == [
        (x.table, len(x.rows)) for x in b.batches
    ]
    assert a.batches[0].rows[:50] == b.batches[0].rows[:50]


def test_non_gbp_donations_only_for_medium_and_large(generated):
    def currencies(org):
        rows = [
            r
            for b in generated[org].batches
            if b.table in ("raw_justgiving_donations", "raw_launchgood_donations")
            for r in b.rows
        ]
        return Counter(
            r.get("currencyCode") or r.get("donation_currency_dc") for r in rows
        )

    assert set(currencies("demo_small")) == {"GBP"}
    assert set(currencies("demo_medium")) - {"GBP"}
    assert set(currencies("demo_large")) - {"GBP"}


def test_refunded_donations_vanish_from_the_second_pull(generated):
    pulls = [
        b
        for b in generated["demo_medium"].batches
        if b.table == "raw_justgiving_donations"
    ]
    first, second = ({r["id"] for r in p.rows} for p in pulls)
    assert second < first
    assert len(first - second) < len(first) * 0.02


def test_most_emails_and_posts_move_nothing(tmp_path):
    from synthetic.marketing import emails_for, posts_for

    for c in CHARITIES:
        emails = emails_for(c, date(2023, 10, 17), END, 11)
        posts = posts_for(c, "instagram", date(2023, 10, 17), END, 11)
        assert sum(1 for e in emails if e.effect) / len(emails) < 0.5
        assert sum(1 for p in posts if p.effect) / len(posts) < 0.3


def test_al_noor_gives_far_more_in_ramadan(tmp_path):
    g = generate(CHARITIES[0], END, seed=5, out_dir=tmp_path, years=3)
    export = next(
        b
        for b in g.batches
        if b.table == "raw_launchgood_donations"
        and b.tags["_source_file"] == "launchgood_export.csv"
    )
    days = [date.fromisoformat(r["created_date_utc"]) for r in export.rows]
    share = sum(calendar.in_ramadan(d) for d in days) / len(days)
    assert share > 0.2  # Ramadan is about 8% of the year


def test_fake_people_use_example_addresses_only(generated):
    emails = {
        r["email"]
        for _, b in all_batches(generated)
        if b.table == "raw_launchgood_donations"
        for r in b.rows
    }
    assert emails and all(e.endswith("@example.com") for e in emails)


def test_justgiving_pages_end_near_their_targets(generated):
    pages = [
        row
        for _, b in all_batches(generated)
        if b.table == "raw_justgiving_pages"
        for row in b.rows
        if float(row["fundraisingTarget"]) > 0
    ]
    assert pages
    for page in pages:
        target = float(page["fundraisingTarget"])
        raised = float(page["grandTotalRaisedExcludingGiftAid"])
        if page["activityCharityCreated"] and raised:
            # A charity's appeal target is set against what it raised
            assert 0.7 <= raised / target <= 1.4, page["title"]
        else:
            # A supporter's page stops collecting near its target
            assert raised <= 3 * target, page["title"]


def test_audience_series_lands_on_its_counts_and_has_dips():
    import random
    from datetime import date, timedelta
    from itertools import pairwise

    from synthetic.rand import audience_series

    start, end = date(2025, 1, 1), date(2025, 12, 31)
    drops = {start + timedelta(days=d): 0.005 for d in range(30, 360, 45)}
    series = audience_series(random.Random(3), start, end, (1000, 1500), {}, drops)
    values = list(series.values())

    assert values[0] == 1000 and 1492 <= values[-1] <= 1508
    assert sum(b < a for a, b in pairwise(values)) >= len(drops)
