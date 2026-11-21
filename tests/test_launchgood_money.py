"""LaunchGood's CSV is all text. Money columns must reach BigQuery as decimals,
or a batch of whole numbers makes the column INTEGER and the next batch fails."""

from ingestion.launchgood_donations import (
    MONEY_COLUMNS,
    coerce_money_columns,
    read_donations_export,
)


def test_whole_numbers_become_decimals():
    row = coerce_money_columns({"zakat_amount_in_donation_currency": "100"})
    assert row["zakat_amount_in_donation_currency"] == 100.0
    assert isinstance(row["zakat_amount_in_donation_currency"], float)


def test_fractions_are_kept():
    row = coerce_money_columns({"donation_amount_in_donation_currency": "12.50"})
    assert row["donation_amount_in_donation_currency"] == 12.5


def test_blank_and_odd_cells_are_left_alone():
    row = coerce_money_columns(
        {
            "zakat_amount_in_donation_currency": "",
            "donation_amount_in_donation_currency": "n/a",
            "total_processing_fees_paid_by_cc_in_settled_currency": "  ",
        }
    )
    assert row["zakat_amount_in_donation_currency"] == ""
    assert row["donation_amount_in_donation_currency"] == "n/a"
    assert row["total_processing_fees_paid_by_cc_in_settled_currency"] == "  "


def test_other_columns_are_not_touched():
    row = coerce_money_columns({"donor_id": "12345", "zakat_yes_or_no": "T"})
    assert row == {"donor_id": "12345", "zakat_yes_or_no": "T"}


def test_the_export_reader_applies_it(tmp_path):
    csv_file = tmp_path / "export.csv"
    csv_file.write_text(
        "Donation Amount (in Donation Currency),Zakat Amount (in Donation Currency),Name\n"
        "25,100,Sam\n30.5,,Alex\n"
    )
    rows = read_donations_export.fn(csv_file)
    assert rows[0]["zakat_amount_in_donation_currency"] == 100.0
    assert rows[0]["donation_amount_in_donation_currency"] == 25.0
    assert rows[1]["donation_amount_in_donation_currency"] == 30.5
    assert rows[1]["zakat_amount_in_donation_currency"] == ""
    assert rows[0]["name"] == "Sam"


def test_every_money_column_is_a_real_export_column():
    # Guards against a typo silently disabling the fix
    with open("synthetic/reference_shapes.json") as f:
        shapes = f.read()
    for column in MONEY_COLUMNS:
        assert column in shapes
