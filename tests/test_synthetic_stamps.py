"""The nightly refresh stamps its latest pull with the real time of the run, so
Data health is only "Out of date" when no run has happened, not whenever a run
is merely late."""

from datetime import UTC, date, datetime, time, timedelta

from synthetic.charities import CHARITIES
from synthetic.generate import generate

END = date(2026, 11, 20)
USUAL = datetime.combine(END, time(6), tzinfo=UTC)


def _stamps(generated):
    """Every pull time in the data batches (the run log has its own test)."""
    out = []
    for b in generated.batches:
        if b.table == "raw_refresh_runs":
            continue
        if b.ingested_at:
            out.append(b.ingested_at)
        out += b.row_ingested_at or []
    return out


def _make(tmp_path, pulled_at=None):
    return generate(CHARITIES[2], END, 42, tmp_path, years=1, pulled_at=pulled_at)


def test_default_stamps_the_latest_pull_at_six_utc(tmp_path):
    g = _make(tmp_path)
    assert max(_stamps(g)) == USUAL


def test_pulled_at_becomes_the_latest_pull_time(tmp_path):
    pulled_at = datetime(2026, 11, 21, 13, 17, tzinfo=UTC)
    g = _make(tmp_path, pulled_at)
    stamps = _stamps(g)
    assert max(stamps) == pulled_at
    assert all(t <= pulled_at for t in stamps)


def test_run_log_is_not_stamped_after_the_run_itself(tmp_path):
    pulled_at = datetime(2026, 11, 21, 7, 17, tzinfo=UTC)
    g = _make(tmp_path, pulled_at)
    log = next(b for b in g.batches if b.table == "raw_refresh_runs")
    assert log.ingested_at == pulled_at
    latest_start = max(datetime.fromisoformat(r["started_at"]) for r in log.rows)
    # Source runs start in the first couple of minutes of the pull
    assert pulled_at <= latest_start <= pulled_at + timedelta(minutes=3)


def test_every_earlier_pull_keeps_its_distance_from_the_latest(tmp_path):
    shift = timedelta(hours=7, minutes=17)
    plain = sorted(_stamps(_make(tmp_path)))
    moved = sorted(_stamps(_make(tmp_path, USUAL + shift)))
    assert [b - a for a, b in zip(plain, moved, strict=True)] == [shift] * len(plain)
