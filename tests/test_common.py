"""Tests for the shared ingestion helpers in ingestion/common.py."""

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest

from ingestion import common
from ingestion.common import (
    MAX_RETRIES,
    coerce_to_float,
    parse_retry_after,
    request_with_retries,
    update_env_file,
)

# --- coerce_to_float ---------------------------------------------------------


def test_coerce_to_float_turns_whole_numbers_into_floats():
    row = {"stats": {"open_rate": 0, "member_count": 6}, "amount": "210"}

    coerce_to_float(row, ["stats.open_rate", "amount"])

    assert row["stats"]["open_rate"] == 0.0
    assert isinstance(row["stats"]["open_rate"], float)
    assert row["amount"] == 210.0
    # fields not named are left exactly as they were
    assert row["stats"]["member_count"] == 6
    assert isinstance(row["stats"]["member_count"], int)


def test_coerce_to_float_ignores_missing_and_null_fields():
    row = {"stats": {"open_rate": None}, "opens": None}

    coerce_to_float(row, ["stats.open_rate", "opens.open_rate", "nothing.here", "x"])

    assert row == {"stats": {"open_rate": None}, "opens": None}


# --- parse_retry_after -------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, 4),  # no header: use the default backoff
        ("7", 7),  # plain seconds
        ("2.5", 2.5),
        ("soon", 4),  # unreadable: use the default
        ("-5", 0),  # never a negative sleep
        ("99999", 120),  # capped
    ],
)
def test_parse_retry_after(header, expected):
    assert parse_retry_after(header, default=4) == expected


def test_parse_retry_after_accepts_an_http_date():
    in_30s = format_datetime(datetime.now(UTC) + timedelta(seconds=30), usegmt=True)
    assert 25 < parse_retry_after(in_30s, default=4) <= 30


def test_parse_retry_after_date_in_the_past_means_no_wait():
    ago_30s = format_datetime(datetime.now(UTC) - timedelta(seconds=30), usegmt=True)
    assert parse_retry_after(ago_30s, default=4) == 0


# --- update_env_file ---------------------------------------------------------


def test_update_env_file_rewrites_in_place_without_duplicating(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nA=1\nTOKEN=old\nB=2\n")

    update_env_file({"TOKEN": "new"}, path=env)

    assert env.read_text() == "# comment\nA=1\nTOKEN=new\nB=2\n"


def test_update_env_file_appends_new_keys_safely_without_trailing_newline(tmp_path):
    # The real bug this function exists to prevent: appending to a file with
    # no trailing newline glued the new key onto the previous line.
    env = tmp_path / ".env"
    env.write_text("A=1")

    update_env_file({"NEW": "x"}, path=env)

    assert env.read_text() == "A=1\nNEW=x\n"


def test_update_env_file_matches_whole_keys_only(tmp_path):
    env = tmp_path / ".env"
    env.write_text("TOKEN_OLD=keep\nTOKEN=old\n")

    update_env_file({"TOKEN": "new"}, path=env)

    assert env.read_text() == "TOKEN_OLD=keep\nTOKEN=new\n"


# --- request_with_retries ----------------------------------------------------
# A fake transport plays back canned responses, so no real API is called,
# and time.sleep is replaced so the tests don't actually wait.


@pytest.fixture
def sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr(common.time, "sleep", calls.append)
    return calls


def client_returning(*responses):
    """An httpx client whose requests get these responses, in order. An
    exception instance in the list is raised instead (e.g. a dropped
    connection)."""
    queue = list(responses)
    seen = []

    def handler(request):
        seen.append(request)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    client = httpx.Client(transport=httpx.MockTransport(handler))
    client.seen = seen
    return client


def test_retries_a_server_error_then_succeeds(sleeps):
    client = client_returning(httpx.Response(503), httpx.Response(200, json={"ok": 1}))

    response = request_with_retries(client, "GET", "https://api.test/x")

    assert response.json() == {"ok": 1}
    assert len(client.seen) == 2
    assert sleeps == [1]  # 2**0 backoff before the second attempt


def test_does_not_retry_a_client_error(sleeps):
    client = client_returning(httpx.Response(404))

    with pytest.raises(httpx.HTTPStatusError):
        request_with_retries(client, "GET", "https://api.test/x")

    assert len(client.seen) == 1  # a 404 won't fix itself; fail fast
    assert sleeps == []


def test_rate_limit_waits_for_retry_after(sleeps):
    client = client_returning(
        httpx.Response(429, headers={"Retry-After": "3"}), httpx.Response(200)
    )

    request_with_retries(client, "GET", "https://api.test/x")

    assert sleeps == [3]


def test_retries_a_dropped_connection(sleeps):
    client = client_returning(httpx.ConnectError("boom"), httpx.Response(200))

    response = request_with_retries(client, "GET", "https://api.test/x")

    assert response.status_code == 200
    assert len(client.seen) == 2


def test_gives_up_after_max_retries(sleeps):
    client = client_returning(*[httpx.Response(500)] * MAX_RETRIES)

    with pytest.raises(httpx.HTTPStatusError):
        request_with_retries(client, "GET", "https://api.test/x")

    assert len(client.seen) == MAX_RETRIES


# --- needs_autodetect --------------------------------------------------------


def _schema():
    from google.cloud import bigquery

    return [
        bigquery.SchemaField("id", "STRING"),
        bigquery.SchemaField(
            "opens", "RECORD", fields=[bigquery.SchemaField("open_rate", "FLOAT")]
        ),
        bigquery.SchemaField(
            "timeseries",
            "RECORD",
            mode="REPEATED",
            fields=[bigquery.SchemaField("unique_opens", "INTEGER")],
        ),
    ]


def test_a_new_table_infers_types():
    from ingestion.common import needs_autodetect

    assert needs_autodetect(None, [{"id": "1"}]) is True


def test_known_fields_keep_the_tables_types_even_if_they_look_numeric():
    from ingestion.common import needs_autodetect

    rows = [
        {
            "id": "4523190765",
            "opens": {"open_rate": 0.4},
            "timeseries": [{"unique_opens": 3}],
        }
    ]
    assert needs_autodetect(_schema(), rows) is False


def test_a_new_field_anywhere_triggers_inference():
    from ingestion.common import needs_autodetect

    assert needs_autodetect(_schema(), [{"id": "x", "new_field": 1}]) is True
    assert needs_autodetect(_schema(), [{"id": "x", "opens": {"new_rate": 1}}]) is True
    assert (
        needs_autodetect(_schema(), [{"id": "x", "timeseries": [{"new": 1}]}]) is True
    )


def test_load_falls_back_to_inference_when_strict_parsing_refuses(monkeypatch):
    from types import SimpleNamespace

    from google.api_core.exceptions import BadRequest
    from google.cloud import bigquery

    from ingestion import common

    attempts = []

    class FakeJob:
        def __init__(self, fail):
            self.fail = fail

        def result(self):
            if self.fail:
                raise BadRequest(
                    "Could not parse '2023-10-18T11:42:16+0000' as a timestamp"
                )

    class FakeClient:
        def get_table(self, table_id):
            return SimpleNamespace(
                schema=[
                    bigquery.SchemaField("timestamp", "TIMESTAMP"),
                    bigquery.SchemaField("_org_id", "STRING"),
                    bigquery.SchemaField("_ingested_at", "TIMESTAMP"),
                ]
            )

        def load_table_from_file(self, payload, table_id, job_config):
            attempts.append(job_config.autodetect)
            return FakeJob(fail=len(attempts) == 1)

    monkeypatch.setattr(common.bigquery, "Client", FakeClient)
    common.load_raw_to_bigquery.fn(
        [{"timestamp": "2023-10-18T11:42:16+0000"}], "p.d.t", {}, org_id="test_charity"
    )

    assert attempts == [False, True]


def test_load_sends_emoji_as_utf8_not_escapes(monkeypatch):
    import gzip

    from google.api_core.exceptions import NotFound

    from ingestion import common

    sent = []

    class FakeJob:
        def result(self):
            pass

    class FakeClient:
        def get_table(self, table_id):
            raise NotFound("no table yet")

        def load_table_from_file(self, payload, table_id, job_config):
            sent.append(gzip.decompress(payload.read()))
            return FakeJob()

    monkeypatch.setattr(common.bigquery, "Client", FakeClient)
    common.load_raw_to_bigquery.fn(
        [{"caption": "Thank you 💛"}], "p.d.t", {}, org_id="test_charity"
    )

    assert "Thank you 💛".encode() in sent[0]
    assert b"\\ud83d" not in sent[0]
