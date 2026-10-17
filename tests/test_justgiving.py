"""Tests for JustGiving-specific helpers."""

from ingestion.justgiving_donations import parse_event_ids


def test_parse_event_ids_splits_and_trims():
    assert parse_event_ids("4100201, 4100202") == ["4100201", "4100202"]


def test_parse_event_ids_drops_blanks_and_repeats_keeping_order():
    assert parse_event_ids("4100202, ,4100201,4100202,") == ["4100202", "4100201"]


def test_parse_event_ids_single_id():
    assert parse_event_ids("4100201") == ["4100201"]
